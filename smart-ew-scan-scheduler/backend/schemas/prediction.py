from pydantic import BaseModel, Field


class BandPrediction(BaseModel):
    band: int
    probability: float = Field(..., ge=0.0, le=1.0)


class PredictionSet(BaseModel):
    time: int
    predictions: list[BandPrediction]
