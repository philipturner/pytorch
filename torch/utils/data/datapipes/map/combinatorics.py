import random

import torch
from torch.utils.data.datapipes.datapipe import IterDataPipe, MapDataPipe
from typing import Iterator, List, Optional, TypeVar

__all__ = ["ShufflerIterDataPipe", ]


T_co = TypeVar('T_co', covariant=True)


class ShufflerIterDataPipe(IterDataPipe[T_co]):
    r"""
    Shuffle the input DataPipe via its indices (functional name: ``shuffle``).

    When it is used with :class:`~torch.utils.data.DataLoader`, the methods to
    set up random seed are different based on :attr:`num_workers`.

    For single-process mode (:attr:`num_workers == 0`), the random seed is set before
    the :class:`~torch.utils.data.DataLoader` in the main process. For multi-process
    mode (:attr:`num_worker > 0`), ``worker_init_fn`` is used to set up a random seed
    for each worker process.

    Args:
        datapipe: MapDataPipe being shuffled
        indices: a list of indices of the MapDataPipe. If not provided, we assume it uses 0-based indexing

    Example:
        >>> from torchdata.datapipes.map import SequenceWrapper
        >>> dp = SequenceWrapper(range(10))
        >>> shuffle_dp = dp.shuffle()
        >>> list(shuffle_dp)
        [0, 4, 1, 6, 3, 2, 9, 5, 7, 8]
    """
    datapipe: MapDataPipe[T_co]
    _enabled: bool
    _seed: Optional[int]
    _rng: random.Random

    def __init__(self,
                 datapipe: MapDataPipe[T_co],
                 *,
                 indices: Optional[List] = None,
                 ) -> None:
        super().__init__()
        self.datapipe = datapipe
        self.indices = list(range(len(datapipe))) if indices is None else indices
        self._enabled = True
        self._seed = None
        self._rng = random.Random()

    def set_shuffle(self, shuffle=True):
        self._enabled = shuffle
        return self

    def set_seed(self, seed: int):
        self._seed = seed
        return self

    def __iter__(self) -> Iterator[T_co]:
        if not self._enabled:
            for idx in self.indices:
                yield self.datapipe[idx]
        else:
            if self._seed is None:
                self._seed = int(torch.empty((), dtype=torch.int64).random_().item())
            self._rng.seed(self._seed)
            self._seed = None
            shuffled_indices = self._rng.sample(self.indices, len(self.indices))
            for idx in shuffled_indices:
                yield self.datapipe[idx]

    def __len__(self) -> int:
        return len(self.datapipe)

    def __getstate__(self):
        if IterDataPipe.getstate_hook is not None:
            return IterDataPipe.getstate_hook(self)
        state = (
            self.datapipe,
            self._enabled,
            self._seed,
            self._valid_iterator_id,
            self._number_of_samples_yielded,
            self._rng.getstate(),
        )
        return state

    def __setstate__(self, state):
        (
            self.datapipe,
            self._enabled,
            self._seed,
            self._valid_iterator_id,
            self._number_of_samples_yielded,
            rng_state,
        ) = state
        self._rng = random.Random()
        self._rng.setstate(rng_state)


MapDataPipe.register_datapipe_as_function("shuffle", ShufflerIterDataPipe)
