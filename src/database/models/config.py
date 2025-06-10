from typing import Union, List, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class Configuration(BaseModel):
    id: int
    type: str
    value: Union[str, int, bool, List[str]]
    data_type: str = Field(..., pattern="^(string|int|bool|list)$")
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

    @field_validator("value", mode="before")
    def cast_value(cls, v, info):
        data_type = info.data.get("data_type", "string")

        if v is None:
            return v

        try:
            if data_type == "int":
                return int(v)
            elif data_type == "bool":
                return str(v).lower() in ("true", "1", "yes")
            elif data_type == "list":
                return [item.strip() for item in str(v).split(",")]
            else:
                return str(v)
        except Exception:
            return v  # fallback to original value

