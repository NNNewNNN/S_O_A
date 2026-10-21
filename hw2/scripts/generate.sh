#!/bin/bash
fastapi-codegen \
  --input src/main/resources/openapi/openapi.yaml \
  --output app/generated \
  --output-model-type pydantic_v2.BaseModel