# Conformance Rules Documentation for Timber Manufacturing OCEL
## HewSaw Sawmill Process Conformance Specification

This document formally specifies the conformance rules used for ground-truth labeling
in the OCEL timber manufacturing conformance prediction task.

---

## 1. Rule Categories

The conformance specification comprises **13 rules** across **5 categories**:

| Category | Code | Count | Description |
|----------|------|-------|-------------|
| Activity Sequence Rules | ASR | 3 | Correct ordering of activities |
| Mandatory Step Rules | MSR | 2 | Required activities that must occur |
| Timing Rules | TR | 3 | SLA and duration constraints |
| Object Flow Rules | OFR | 2 | Correct object interactions |
| Quality Rules | QR | 2 | Quality thresholds and limits |
| Resource Rules | RR | 1 | Equipment and operator constraints |

---

## 2. Rule Definitions

### 2.1 Activity Sequence Rules (ASR)

#### ASR-1: Quality Before Completion
- **Severity**: HIGH
- **Description**: QualityInspection or QualitySorting must occur before ProductionComplete
- **Formal Definition**: 
  ```
  ∀ case c: ProductionComplete ∈ c → ∃ QualityActivity ∈ c ∧ 
            time(QualityActivity) < time(ProductionComplete)
  where QualityActivity ∈ {QualityInspection, QualitySorting}
  ```
- **Rationale**: Products cannot be marked complete without quality verification
- **Violation Impact**: Product released without quality assurance

#### ASR-2: Start Before Process
- **Severity**: MEDIUM
- **Description**: StartProduction must occur before ProcessLogs in a valid production sequence
- **Formal Definition**:
  ```
  ∀ case c: ProcessLogs ∈ c → ∃ StartProduction ∈ c ∧ 
            time(StartProduction) < time(first(ProcessLogs))
  ```
- **Rationale**: Production logging requires proper initialization
- **Violation Impact**: Process data may be incomplete or untracked

#### ASR-3: Maintenance Before Resume
- **Severity**: HIGH
- **Description**: After breakdown, maintenance must occur before production resumes
- **Formal Definition**:
  ```
  ∀ case c: Breakdown ∈ c → ∃ Maintenance ∈ c ∧
            time(Breakdown) < time(Maintenance) < time(next(ProcessLogs))
  where Breakdown ∈ {BreakdownMechanical, BreakdownElectrical}
  ```
- **Rationale**: Equipment must be repaired before resuming operations
- **Violation Impact**: Safety hazard, product damage

---

### 2.2 Mandatory Step Rules (MSR)

#### MSR-1: Quality Check Required
- **Severity**: HIGH
- **Description**: Every completed production batch must have at least one quality activity
- **Formal Definition**:
  ```
  ∀ case c: ProductionComplete ∈ c → 
            |{QualityInspection, QualitySorting} ∩ activities(c)| ≥ 1
  ```
- **Rationale**: All output must undergo quality verification
- **Violation Impact**: Unverified products may reach customers

#### MSR-2: Shift Boundary Required
- **Severity**: MEDIUM
- **Description**: Production runs spanning >8 hours must include ShiftEnd events
- **Formal Definition**:
  ```
  ∀ case c: duration(c) > 8 hours → ShiftEnd ∈ activities(c)
  ```
- **Rationale**: Shift handovers must be documented
- **Violation Impact**: Accountability gaps, fatigue-related issues

---

### 2.3 Timing Rules (TR)

#### TR-1: Maintenance Efficiency
- **Severity**: LOW
- **Description**: MaintenanceHours should not exceed 2× DowntimeHours
- **Formal Definition**:
  ```
  ∀ event e: MaintenanceHours(e) ≤ 2 × DowntimeHours(e)
  ```
- **Rationale**: Excessive maintenance time indicates inefficiency
- **Violation Impact**: Productivity loss, cost overruns

#### TR-2: Production Yield Threshold
- **Severity**: HIGH
- **Description**: YieldPercent must be ≥25% for valid production
- **Formal Definition**:
  ```
  ∀ event e ∈ ProductionBatch: YieldPercent(e) ≥ 25
  ```
- **Rationale**: Below 25% indicates major process issues
- **Violation Impact**: Excessive waste, quality issues
- **Threshold Justification**: Industry standard for timber recovery is 40-60%; 25% is the absolute minimum acceptable

#### TR-3: Excessive Downtime Alert
- **Severity**: MEDIUM  
- **Description**: DowntimeHours exceeding 4 hours requires investigation
- **Formal Definition**:
  ```
  ∀ event e: DowntimeHours(e) ≤ 4
  ```
- **Rationale**: Long downtimes indicate serious equipment/process issues
- **Violation Impact**: Production delays, SLA breaches

---

### 2.4 Object Flow Rules (OFR)

#### OFR-1: Object Type Consistency
- **Severity**: HIGH
- **Description**: Each event must be associated with exactly one primary object type
- **Formal Definition**:
  ```
  ∀ event e: |{obj_type(e)}| = 1
  ```
- **Rationale**: OCEL structure requires unambiguous object assignment
- **Violation Impact**: Data integrity issues

#### OFR-2: Mill Assignment Consistency
- **Severity**: MEDIUM
- **Description**: Within a case, Mill should not change without handover
- **Formal Definition**:
  ```
  ∀ case c: |unique(Mill(activities(c)))| ≤ 2
  ```
- **Rationale**: Logs should be processed on consistent equipment
- **Violation Impact**: Traceability loss

---

### 2.5 Quality Rules (QR)

#### QR-1: Quality Grade Threshold
- **Severity**: MEDIUM
- **Description**: QualityGradeA must be ≥60% for acceptable production
- **Formal Definition**:
  ```
  ∀ event e: QualityGradeA(e) ≥ 60
  ```
- **Rationale**: Below 60% grade-A indicates excessive defects
- **Violation Impact**: Revenue loss from lower-grade products
- **Threshold Justification**: Based on HewSaw quality standards for primary timber products

#### QR-2: Defect Rate Limits
- **Severity**: HIGH
- **Description**: Individual defect rates should not exceed 8%
- **Formal Definition**:
  ```
  ∀ rate ∈ {MoistureDefectRate, TwistingDefectRate, BlueStainRate, 
            KnotDefectRate, CrackDefectRate}: rate ≤ 8%
  ```
- **Rationale**: High defect rates indicate process control issues
- **Violation Impact**: Customer complaints, warranty claims
- **Defect Categories**:
  - **Moisture**: Improper drying, risk of warping
  - **Twisting**: Grain irregularities, structural weakness
  - **BlueStain**: Fungal discoloration, aesthetic issues
  - **Knot**: Natural defects affecting strength
  - **Crack**: Structural integrity concerns

---

### 2.6 Resource Rules (RR)

#### RR-1: Equipment Status Validity
- **Severity**: HIGH
- **Description**: Maintenance activities must have appropriate equipment status
- **Formal Definition**:
  ```
  ∀ event e where activity(e) ∈ {MaintenancePlanned, MaintenanceUnplanned,
                                  SawBladeChange, ConveyorMaintenance}:
    EquipmentStatus(e) ∈ {Maintenance, Breakdown}
  ```
- **Rationale**: Status must reflect actual equipment state
- **Violation Impact**: Misreported equipment availability

---

## 3. Conformance Labeling Procedure

### 3.1 Event-Level Labeling
Each event e receives a label y ∈ {0, 1}:
- **y = 0 (Conformant)**: No rule violations detected in the case containing e
- **y = 1 (Non-Conformant)**: At least one rule violation in the case

### 3.2 Case-Level Aggregation
```python
def evaluate_case_conformance(case_events, case_activities):
    violations = []
    
    # Check each rule
    for rule in CONFORMANCE_RULES:
        if rule.is_violated(case_events, case_activities):
            violations.append(rule.id)
    
    # Binary label: 0 if no violations, 1 otherwise
    label = 1 if len(violations) > 0 else 0
    
    return label, violations
```

### 3.3 Ground Truth Generation
Ground truth labels are derived automatically by:
1. Processing each case sequentially
2. Evaluating all 13 rules against case data
3. Assigning label based on rule evaluation
4. Propagating case-level label to all events in case

---

## 4. Dataset Statistics

### 4.1 Generated Dataset
| Metric | Value |
|--------|-------|
| Total Events | ~10,900 |
| Total Cases | 400 |
| Conformant Events | ~74% |
| Non-Conformant Events | ~26% |
| Date Range | 2012-2021 |

### 4.2 Violation Distribution
| Rule | Occurrences | % of Violations |
|------|-------------|-----------------|
| TR-2 (Yield < 25%) | ~2,700 | ~45% |
| QR-2 (Defect > 8%) | ~2,400 | ~40% |
| QR-1 (Grade < 60%) | ~800 | ~13% |
| ASR-1 (No Quality Check) | ~30 | ~0.5% |
| MSR-1 (Missing Quality) | ~30 | ~0.5% |

---

## 5. Validation Considerations

### 5.1 Rule Threshold Sensitivity
All thresholds (25% yield, 8% defect, 60% grade, 4h downtime) are based on:
- Industry standards for timber processing
- HewSaw operational guidelines
- Domain expert consultation

### 5.2 Label Quality
- Labels are deterministic given the rule specifications
- No human annotation required (rule-based)
- Inter-annotator agreement: N/A (automated)

### 5.3 Temporal Validity
Rules are applied to historical data (2012-2021) and assumed to be stable over this period.

---

## 6. Usage in Conformance Prediction

The conformance labels enable:
1. **Binary Classification**: Predict y ∈ {0, 1} for streaming events
2. **Early Warning**: Identify cases at risk of violation before completion
3. **Root Cause Analysis**: Violation_Types field identifies which rules triggered

### 6.1 Feature Engineering
Conformance-aware features derived from rules:
- `ProcessCompliance`: Event sequence rule adherence score
- `ActivityDeviation`: Distance from expected activity patterns
- `ObjectFlowViolation`: Object interaction anomaly count
- `QualityRiskScore`: Aggregate defect and grade risk

---

**Document Version**: 1.0
**Last Updated**: 2026-01-13
**Author**: Generated for OCEL Paper Enhancement
