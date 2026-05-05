from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class MeterInfo(BaseModel):
    filename: str
    records: int
    std: float
    period_start: str
    period_end: str

class DatasetSummary(BaseModel):
    meters_loaded: int
    total_records: int
    period_start: str
    period_end: str
    std: float
    mean: float

class ModelResult(BaseModel):
    name: str
    mae: float
    rmse: Optional[float]
    order: Optional[str]
    config: Optional[Dict[str, Any]]
    selected: bool

class ForecastPoint(BaseModel):
    timestamp: str
    forecast_energy: float

class OptimizationPoint(BaseModel):
    timestamp: str
    forecast_energy: float
    optimized_energy: float

class DeviceSchedule(BaseModel):
    name: str
    start_time: str
    duration_minutes: int
    power_kwh: float
    cost_rs: float

class ImpactMetrics(BaseModel):
    energy_saved: float
    energy_saved_kwh: float
    cost_saved: float
    carbon_saved: float
    peak_before: float
    peak_after: float
    peak_before_kwh: float
    peak_after_kwh: float
    peak_reduction_pct: float
    lf_before: float
    lf_after: float
    lf_improvement: float
    annual_cost: float
    annual_carbon: float

class PipelineResponse(BaseModel):
    status: str
    dataset: DatasetSummary
    models: List[ModelResult]
    selected_model: str
    adf_stationary: bool
    forecast: List[ForecastPoint]
    optimization: List[OptimizationPoint]
    devices: List[DeviceSchedule]
    impact: ImpactMetrics