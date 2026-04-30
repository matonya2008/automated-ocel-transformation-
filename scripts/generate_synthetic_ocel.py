"""
OCEL Timber Manufacturing Data Simulator with Conformance Labeling
===================================================================
This script generates synthetic OCEL data for timber manufacturing with
explicit conformance rules and ground truth labels.

Author: Generated for OCEL Paper Enhancement
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import json
from pathlib import Path

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "sample"
DOCS_DIR = REPO_ROOT / "docs"

# =============================================================================
# CONFORMANCE RULES DEFINITION
# =============================================================================
"""
CONFORMANCE RULES FOR TIMBER MANUFACTURING OCEL

These rules encode domain-specific conformance requirements for the HewSaw
timber manufacturing process. Each rule is formally defined with:
- Rule ID and Name
- Formal Definition
- Violation Detection Logic
- Severity Level

RULE CATEGORIES:
1. Activity Sequence Rules (ASR): Correct ordering of activities
2. Mandatory Step Rules (MSR): Required activities that must occur
3. Timing Rules (TR): SLA and duration constraints
4. Object Flow Rules (OFR): Correct object interactions
5. Resource Rules (RR): Equipment and operator constraints
"""

CONFORMANCE_RULES = {
    "ASR-1": {
        "name": "Quality Before Completion",
        "description": "QualityInspection or QualitySorting must occur before ProductionComplete",
        "severity": "HIGH",
        "formula": "∀ case c: ProductionComplete ∈ c → ∃ QualityInspection ∈ c ∧ time(QualityInspection) < time(ProductionComplete)"
    },
    "ASR-2": {
        "name": "Start Before Process",
        "description": "StartProduction must occur before ProcessLogs in a valid production sequence",
        "severity": "MEDIUM",
        "formula": "∀ case c: ProcessLogs ∈ c → ∃ StartProduction ∈ c ∧ time(StartProduction) < time(first ProcessLogs)"
    },
    "ASR-3": {
        "name": "Maintenance Before Resume",
        "description": "After BreakdownMechanical/BreakdownElectrical, MaintenancePlanned/MaintenanceUnplanned must occur before ProcessLogs resumes",
        "severity": "HIGH",
        "formula": "∀ case c: Breakdown × ∈ c → ∃ Maintenance × ∈ c ∧ time(Maintenance) > time(Breakdown) ∧ time(Maintenance) < time(next ProcessLogs)"
    },
    "MSR-1": {
        "name": "Quality Check Required",
        "description": "Every completed production batch must have at least one quality activity",
        "severity": "HIGH",
        "formula": "∀ case c: ProductionComplete ∈ c → |{QualityInspection, QualitySorting} ∩ c| ≥ 1"
    },
    "MSR-2": {
        "name": "Shift Boundary Required",
        "description": "Production runs spanning >8 hours must include ShiftEnd events",
        "severity": "MEDIUM",
        "formula": "∀ case c: duration(c) > 8h → ShiftEnd ∈ c"
    },
    "TR-1": {
        "name": "Maintenance Duration Limit",
        "description": "MaintenanceHours should not exceed 2x the DowntimeHours (efficiency rule)",
        "severity": "LOW",
        "formula": "∀ event e: MaintenanceHours(e) ≤ 2 × DowntimeHours(e)"
    },
    "TR-2": {
        "name": "Production Yield Threshold",
        "description": "YieldPercent must be ≥25% for valid production (below indicates major issues)",
        "severity": "HIGH",
        "formula": "∀ event e ∈ ProductionBatch: YieldPercent(e) ≥ 25"
    },
    "TR-3": {
        "name": "Excessive Downtime Alert",
        "description": "DowntimeHours exceeding 4 hours indicates conformance violation requiring investigation",
        "severity": "MEDIUM",
        "formula": "∀ event e: DowntimeHours(e) ≤ 4"
    },
    "OFR-1": {
        "name": "Object Type Consistency",
        "description": "Each event must be associated with exactly one primary object type",
        "severity": "HIGH",
        "formula": "∀ event e: |{obj_type(e)}| = 1"
    },
    "OFR-2": {
        "name": "Mill Assignment Consistency",
        "description": "Within a case, Mill should not change without explicit handover",
        "severity": "MEDIUM",
        "formula": "∀ case c: |unique(Mill(c))| ≤ 2 (allowing for handovers)"
    },
    "RR-1": {
        "name": "Equipment Status Validity",
        "description": "Maintenance activities must have EquipmentStatus = 'Maintenance' or 'Breakdown'",
        "severity": "HIGH",
        "formula": "∀ event e ∈ {MaintenancePlanned, MaintenanceUnplanned, SawBladeChange, ConveyorMaintenance}: EquipmentStatus(e) ∈ {Maintenance, Breakdown}"
    },
    "QR-1": {
        "name": "Quality Grade Threshold",
        "description": "QualityGradeA must be ≥60% for acceptable production",
        "severity": "MEDIUM",
        "formula": "∀ event e: QualityGradeA(e) ≥ 60"
    },
    "QR-2": {
        "name": "Defect Rate Limits",
        "description": "Individual defect rates should not exceed 8% (critical quality issue)",
        "severity": "HIGH",
        "formula": "∀ defect_rate ∈ {Moisture, Twisting, BlueStain, Knot, Crack}: rate ≤ 8%"
    }
}

# =============================================================================
# DATA GENERATION PARAMETERS
# =============================================================================

ACTIVITIES = [
    'ProcessLogs', 'ShiftEnd', 'ProductionComplete', 'StartProduction',
    'QualitySorting', 'QualityInspection', 'LogShortage', 'MaintenancePlanned',
    'MaintenanceUnplanned', 'ConveyorMaintenance', 'SawBladeChange',
    'BreakdownMechanical', 'BreakdownElectrical'
]

MILLS = ['R200', 'R250']
SHIFTS = ['Day', 'Night']
OPERATORS = [f'OP_{str(i).zfill(3)}' for i in range(1, 16)]
EQUIPMENT_STATUS = ['Operational', 'Maintenance', 'Breakdown']

# Activity probabilities (based on original data distribution)
ACTIVITY_PROBS = {
    'ProcessLogs': 0.28,
    'ShiftEnd': 0.12,
    'ProductionComplete': 0.11,
    'StartProduction': 0.10,
    'QualitySorting': 0.10,
    'QualityInspection': 0.10,
    'LogShortage': 0.08,
    'MaintenancePlanned': 0.04,
    'MaintenanceUnplanned': 0.02,
    'ConveyorMaintenance': 0.02,
    'SawBladeChange': 0.01,
    'BreakdownMechanical': 0.01,
    'BreakdownElectrical': 0.01
}

# Object type mapping
OBJECT_TYPE_MAP = {
    'ProcessLogs': 'ProductionBatch',
    'ProductionComplete': 'ProductionBatch',
    'StartProduction': 'ProductionBatch',
    'ShiftEnd': 'LogBatch',
    'LogShortage': 'LogBatch',
    'QualitySorting': 'QualityReport',
    'QualityInspection': 'QualityReport',
    'MaintenancePlanned': 'MaintenanceRecord',
    'MaintenanceUnplanned': 'MaintenanceRecord',
    'ConveyorMaintenance': 'MaintenanceRecord',
    'SawBladeChange': 'MaintenanceRecord',
    'BreakdownMechanical': 'MaintenanceRecord',
    'BreakdownElectrical': 'MaintenanceRecord'
}

# =============================================================================
# DATA GENERATION FUNCTIONS
# =============================================================================

def generate_case_events(case_id, start_date, num_events, introduce_violations=False):
    """Generate events for a single case with optional conformance violations."""
    events = []
    current_time = start_date
    mill = random.choice(MILLS)
    
    # Determine if this case will have violations
    has_violation = introduce_violations and random.random() < 0.35  # 35% violation rate within flagged cases
    violation_types = []
    
    # Generate activity sequence
    activities_in_case = []
    has_quality_check = False
    has_start = False
    has_breakdown = False
    breakdown_resolved = True
    
    for i in range(num_events):
        # Select activity with constraints
        if i == 0 and random.random() < 0.7:
            activity = 'StartProduction'
            has_start = True
        elif has_breakdown and not breakdown_resolved and random.random() < 0.8:
            activity = random.choice(['MaintenancePlanned', 'MaintenanceUnplanned'])
            breakdown_resolved = True
        else:
            activity = np.random.choice(
                list(ACTIVITY_PROBS.keys()),
                p=list(ACTIVITY_PROBS.values())
            )
        
        # Track state
        if activity in ['QualityInspection', 'QualitySorting']:
            has_quality_check = True
        if activity in ['BreakdownMechanical', 'BreakdownElectrical']:
            has_breakdown = True
            breakdown_resolved = False
        if activity in ['MaintenancePlanned', 'MaintenanceUnplanned', 'ConveyorMaintenance', 'SawBladeChange']:
            breakdown_resolved = True
            
        activities_in_case.append(activity)
        
        # Generate event attributes
        # Inject violations more frequently in flagged cases
        inject_violation_now = has_violation and random.random() < 0.4  # 40% of events in flagged cases
        event = generate_event_attributes(
            case_id, i, activity, current_time, mill, 
            inject_violation_now
        )
        events.append(event)
        
        # Advance time
        time_delta = timedelta(
            hours=random.uniform(0.5, 4),
            minutes=random.randint(0, 59)
        )
        current_time += time_delta
    
    # Determine conformance label based on rules
    conformance_label, violations = evaluate_case_conformance(events, activities_in_case)
    
    # Add conformance label to all events in case
    for event in events:
        event['Conformance_Label'] = conformance_label
        event['Violation_Types'] = '|'.join(violations) if violations else 'None'
    
    return events

def generate_event_attributes(case_id, event_idx, activity, timestamp, mill, inject_violation=False):
    """Generate realistic attributes for a single event."""
    
    # Determine object type
    obj_type = OBJECT_TYPE_MAP.get(activity, 'Mill')
    
    # Generate object IDs
    obj_ids = {
        'ocel:type:MaintenanceRecord': '',
        'ocel:type:LogBatch': '',
        'ocel:type:ProductionBatch': '',
        'ocel:type:TimberOutput': '',
        'ocel:type:QualityReport': '',
        'ocel:type:Mill': ''
    }
    
    if obj_type == 'MaintenanceRecord':
        obj_ids['ocel:type:MaintenanceRecord'] = f'MR_{mill}_{event_idx:03d}'
    elif obj_type == 'LogBatch':
        obj_ids['ocel:type:LogBatch'] = f'LOG_{mill}_{event_idx:03d}'
    elif obj_type == 'ProductionBatch':
        obj_ids['ocel:type:ProductionBatch'] = f'BATCH_{case_id}_{event_idx:03d}'
    elif obj_type == 'QualityReport':
        obj_ids['ocel:type:QualityReport'] = f'QR_{case_id}_{event_idx:03d}'
    elif obj_type == 'TimberOutput':
        obj_ids['ocel:type:TimberOutput'] = f'TO_{mill}_{event_idx:03d}'
    else:
        obj_ids['ocel:type:Mill'] = f'MILL_{mill}'
    
    # Generate operational metrics
    logs_processed = random.randint(50, 220)
    volume_m3 = round(random.uniform(8, 60), 2)
    production_m3 = round(volume_m3 * random.uniform(0.25, 0.80), 2)
    yield_percent = round((production_m3 / volume_m3) * 100, 2) if volume_m3 > 0 else 25
    
    # Inject violations if requested
    if inject_violation:
        violation_type = random.choice(['yield', 'downtime', 'defect', 'quality'])
        if violation_type == 'yield':
            yield_percent = round(random.uniform(15, 24), 2)  # Below 25% threshold
        elif violation_type == 'downtime':
            downtime_hours = round(random.uniform(5, 15), 2)  # Above 4 hour threshold
        elif violation_type == 'defect':
            # Will be set below
            pass
    
    # Downtime and maintenance
    if activity in ['MaintenancePlanned', 'MaintenanceUnplanned', 'ConveyorMaintenance', 
                    'SawBladeChange', 'BreakdownMechanical', 'BreakdownElectrical']:
        downtime_hours = round(random.uniform(0.5, 3.5), 2)  # Reduced max to 3.5
        maintenance_hours = round(downtime_hours * random.uniform(0.5, 1.0), 2)
        equipment_status = 'Breakdown' if 'Breakdown' in activity else 'Maintenance'
    else:
        downtime_hours = round(random.uniform(0, 1.5), 2)  # Reduced max to 1.5
        maintenance_hours = round(downtime_hours * random.uniform(0, 0.5), 2)
        equipment_status = 'Operational'
    
    # Defect rates
    if inject_violation and random.random() < 0.3:
        # Inject high defect rate
        defect_type = random.choice(['moisture', 'twisting', 'bluestain', 'knot', 'crack'])
        base_defect = random.uniform(9, 18)  # Above 8% threshold
    else:
        base_defect = 0
    
    moisture_defect = round(random.uniform(0, 5) + (base_defect if base_defect > 0 and random.random() < 0.3 else 0), 2)
    twisting_defect = round(random.uniform(0, 4), 2)
    bluestain_defect = round(random.uniform(0, 4), 2)
    knot_defect = round(random.uniform(0, 5) + (base_defect if base_defect > 0 and random.random() < 0.3 else 0), 2)
    crack_defect = round(random.uniform(0, 4), 2)
    
    # Quality grade (inverse of defects)
    total_defect_rate = moisture_defect + twisting_defect + bluestain_defect + knot_defect + crack_defect
    quality_grade_a = max(50, min(95, round(100 - total_defect_rate * 1.2 + random.uniform(-3, 8), 2)))
    
    # Shift and time attributes
    hour = timestamp.hour
    shift_type = 'Day' if 6 <= hour < 18 else 'Night'
    day_of_week = timestamp.weekday()
    
    event = {
        'ocel:eid': f'E{event_idx:06d}',
        'ocel:activity': activity,
        'ocel:timestamp': timestamp.strftime('%m/%d/%Y %H:%M'),
        **obj_ids,
        'CaseID': case_id,
        'Mill': mill,
        'LogsProcessed': logs_processed,
        'VolumeM3': volume_m3,
        'ProductionM3': production_m3,
        'YieldPercent': yield_percent,
        'DowntimeHours': downtime_hours,
        'MaintenanceHours': maintenance_hours,
        'MoistureDefectRate': moisture_defect,
        'TwistingDefectRate': twisting_defect,
        'BlueStainRate': bluestain_defect,
        'KnotDefectRate': knot_defect,
        'CrackDefectRate': crack_defect,
        'QualityGradeA': quality_grade_a,
        'ShiftType': shift_type,
        'OperatorID': random.choice(OPERATORS),
        'EquipmentStatus': equipment_status,
        'Hour': hour,
        'DayOfWeek': day_of_week
    }
    
    return event

def evaluate_case_conformance(events, activities):
    """Evaluate conformance of a case against all rules."""
    violations = []
    
    # ASR-1: Quality Before Completion
    has_production_complete = 'ProductionComplete' in activities
    has_quality = any(a in activities for a in ['QualityInspection', 'QualitySorting'])
    if has_production_complete:
        pc_idx = activities.index('ProductionComplete')
        quality_before = any(
            activities.index(a) < pc_idx 
            for a in ['QualityInspection', 'QualitySorting'] 
            if a in activities
        )
        if not quality_before and not has_quality:
            violations.append('ASR-1')
    
    # MSR-1: Quality Check Required
    if has_production_complete and not has_quality:
        violations.append('MSR-1')
    
    # TR-2: Production Yield Threshold
    for event in events:
        if event['YieldPercent'] < 25:
            violations.append('TR-2')
            break
    
    # TR-3: Excessive Downtime
    for event in events:
        if event['DowntimeHours'] > 4:
            violations.append('TR-3')
            break
    
    # QR-1: Quality Grade Threshold
    for event in events:
        if event['QualityGradeA'] < 60:
            violations.append('QR-1')
            break
    
    # QR-2: Defect Rate Limits
    for event in events:
        if any([
            event['MoistureDefectRate'] > 8,
            event['TwistingDefectRate'] > 8,
            event['BlueStainRate'] > 8,
            event['KnotDefectRate'] > 8,
            event['CrackDefectRate'] > 8
        ]):
            violations.append('QR-2')
            break
    
    # RR-1: Equipment Status Validity
    maintenance_activities = ['MaintenancePlanned', 'MaintenanceUnplanned', 
                             'ConveyorMaintenance', 'SawBladeChange']
    for i, event in enumerate(events):
        if activities[i] in maintenance_activities:
            if event['EquipmentStatus'] not in ['Maintenance', 'Breakdown']:
                violations.append('RR-1')
                break
    
    # Conformance label: 0 = conformant, 1 = non-conformant
    conformance_label = 1 if violations else 0
    
    return conformance_label, list(set(violations))

def generate_full_dataset(num_events=10000, num_cases=None):
    """Generate a complete OCEL dataset."""
    
    if num_cases is None:
        num_cases = num_events // 20  # Average ~20 events per case
    
    all_events = []
    event_counter = 0
    
    # Start date range
    start_date = datetime(2012, 1, 1)
    end_date = datetime(2021, 12, 31)
    date_range = (end_date - start_date).days
    
    print(f"Generating {num_events} events across {num_cases} cases...")
    
    events_per_case = num_events // num_cases
    remaining_events = num_events % num_cases
    
    for case_idx in range(num_cases):
        case_id = f'CASE_{case_idx:04d}'
        
        # Random start date within range
        case_start = start_date + timedelta(days=random.randint(0, date_range))
        
        # Number of events for this case
        n_events = events_per_case + (1 if case_idx < remaining_events else 0)
        n_events = max(5, min(50, n_events + random.randint(-5, 10)))
        
        # Generate with some cases having violations
        introduce_violations = random.random() < 0.70  # 70% of cases may have violations
        
        case_events = generate_case_events(
            case_id, case_start, n_events, 
            introduce_violations=introduce_violations
        )
        
        # Update event IDs globally
        for event in case_events:
            event['ocel:eid'] = f'E{event_counter:06d}'
            event_counter += 1
        
        all_events.extend(case_events)
        
        if (case_idx + 1) % 100 == 0:
            print(f"  Generated {case_idx + 1}/{num_cases} cases...")
    
    return all_events

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    # Generate expanded dataset
    print("="*60)
    print("OCEL Timber Manufacturing Data Simulator")
    print("="*60)
    
    # Generate 50,000 events for comprehensive validation
    events = generate_full_dataset(num_events=50000, num_cases=2000)
    
    # Convert to DataFrame
    df = pd.DataFrame(events)
    
    # Report statistics
    print("\n" + "="*60)
    print("DATASET STATISTICS")
    print("="*60)
    print(f"Total Events: {len(df)}")
    print(f"Total Cases: {df['CaseID'].nunique()}")
    print(f"Date Range: {df['ocel:timestamp'].min()} to {df['ocel:timestamp'].max()}")
    print(f"\nConformance Distribution:")
    print(df['Conformance_Label'].value_counts())
    print(f"\nConformance Rate: {(df['Conformance_Label']==0).mean()*100:.1f}%")
    print(f"Non-Conformance Rate: {(df['Conformance_Label']==1).mean()*100:.1f}%")
    
    # Violation breakdown
    print("\nViolation Types Distribution:")
    all_violations = df[df['Violation_Types'] != 'None']['Violation_Types'].str.split('|').explode()
    if len(all_violations) > 0:
        print(all_violations.value_counts())
    
    # Activity distribution
    print("\nActivity Distribution:")
    print(df['ocel:activity'].value_counts())
    
    # Save to CSV
    output_file = DATA_DIR / "expanded_timber_ocel_10k.csv"
    df.to_csv(output_file, index=False)
    print(f"\n✓ Dataset saved to: {output_file}")
    
    # Save conformance rules documentation
    rules_file = DOCS_DIR / "conformance_rules_documentation.json"
    with open(rules_file, 'w') as f:
        json.dump(CONFORMANCE_RULES, f, indent=2)
    print(f"✓ Conformance rules saved to: {rules_file}")
    
    print("\n" + "="*60)
    print("GENERATION COMPLETE")
    print("="*60)
