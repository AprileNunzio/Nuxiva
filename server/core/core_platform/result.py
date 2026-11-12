from dataclasses import dataclass
from typing import Callable, Generic, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E", bound=Exception)


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    value: T

    @property
    def is_ok(self) -> bool:
        return True

    def map(self, transform: Callable[[T], U]) -> "Ok[U]":
        return Ok(transform(self.value))

    def and_then(self, step: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return step(self.value)

    def unwrap_or(self, fallback: T) -> T:
        return self.value

    def unwrap(self) -> T:
        return self.value


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    error: E

    @property
    def is_ok(self) -> bool:
        return False

    def map(self, transform: Callable[[T], U]) -> "Err[E]":
        return self

    def and_then(self, step: Callable[[T], "Result[U, E]"]) -> "Err[E]":
        return self

    def unwrap_or(self, fallback: T) -> T:
        return fallback

    def unwrap(self) -> T:
        raise self.error


Result = Union[Ok[T], Err[E]]
