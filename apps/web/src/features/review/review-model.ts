import type { IEPRecord } from "../../lib/types/generated";

export type ReviewGroup = "Identity and dates" | "Accommodations" | "Services" | "Goals";

export interface ReviewField {
  key: string;
  group: ReviewGroup;
  label: string;
  value: string | null;
  confidence: number;
  sourcePage: number | null;
  sourceQuote: string | null;
  sourceIndex: number;
  reconciliationStatus: "matched" | "new" | "ambiguous" | null;
  scopeReferences: IEPRecord["accommodations"][number]["applies_to_refs"];
}

export function buildReviewFields(record: IEPRecord): ReviewField[] {
  const identity: ReviewField[] = [
    scalarField("student_ref", "Student reference", record.student_ref, record.field_confidences.student_ref),
    scalarField("disability_category", "Disability category", record.disability_category, record.field_confidences.disability_category),
    scalarField("school_year", "School year", record.school_year, record.field_confidences.school_year),
    scalarField("annual_review", "Annual review", record.dates.annual_review, record.field_confidences.annual_review),
    scalarField("triennial_reeval", "Triennial reevaluation", record.dates.triennial_reeval, record.field_confidences.triennial_reeval),
    scalarField("last_progress_report", "Last progress report", record.dates.last_progress_report, record.field_confidences.last_progress_report),
  ];
  const accommodations = record.accommodations.map<ReviewField>((item, index) => ({
    key: `accommodation-${item.id}`,
    group: "Accommodations",
    label: `Accommodation ${index + 1}`,
    value: item.text,
    confidence: item.confidence,
    sourcePage: item.source_page,
    sourceQuote: item.source_quote,
    sourceIndex: index,
    reconciliationStatus: item.reconciliation_status,
    scopeReferences: item.applies_to_refs,
  }));
  const services = record.services.map<ReviewField>((item, index) => ({
    key: `service-${item.id}`,
    group: "Services",
    label: item.type,
    value: `${item.minutes_per_week} minutes/week · ${item.frequency} · ${item.provider_role}`,
    confidence: item.confidence,
    sourcePage: item.source_page,
    sourceQuote: item.source_quote,
    sourceIndex: index,
    reconciliationStatus: item.reconciliation_status,
    scopeReferences: [],
  }));
  const goals = record.goals.map<ReviewField>((item, index) => ({
    key: `goal-${item.id}`,
    group: "Goals",
    label: `Goal ${index + 1}`,
    value: item.text,
    confidence: item.confidence,
    sourcePage: item.source_page,
    sourceQuote: item.source_quote,
    sourceIndex: index,
    reconciliationStatus: item.reconciliation_status,
    scopeReferences: [],
  }));
  return [...identity, ...accommodations, ...services, ...goals];
}

export function requiresReview(field: ReviewField, threshold = 0.9): boolean {
  return (
    field.confidence < threshold ||
    field.reconciliationStatus === "ambiguous" ||
    field.scopeReferences.some((scope) => scope.confidence < threshold)
  );
}

function scalarField(key: string, label: string, value: string | null, confidence: number): ReviewField {
  return {
    key,
    group: "Identity and dates",
    label,
    value,
    confidence,
    sourcePage: null,
    sourceQuote: null,
    sourceIndex: 0,
    reconciliationStatus: null,
    scopeReferences: [],
  };
}
