from dataclasses import asdict, dataclass
from typing import List

from zgw_consumers.api_models.base import ZGWModel, factory


@dataclass
class ChildAggregation(ZGWModel):
    key: str
    doc_count: str


@dataclass
class ParentChildBuckets(ZGWModel):
    buckets: List[ChildAggregation]


@dataclass
class FlattenedNestedAggregation(ZGWModel):
    parent_key: str
    child_key: str
    doc_count: str


@dataclass
class ParentAggregation(ChildAggregation):
    key: str
    doc_count: str
    child: ParentChildBuckets

    @property
    def flattened_child_buckets(self) -> List[FlattenedNestedAggregation]:
        return factory(
            FlattenedNestedAggregation,
            [
                {**asdict(bucket), "parent_key": self.key, "child_key": bucket.key}
                for bucket in self.child.buckets
            ],
        )
