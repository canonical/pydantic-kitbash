import pydantic


class MockModel(pydantic.BaseModel):
    mock_field: str = pydantic.Field(
        description="description",
        examples=["val1", "val2"],
        alias="test",
        deprecated="ew.",
    )
