import iepRecord from "../../../data/synthetic/ground_truth/RIV-1001.iep.json";
import generatedRegistry from "./generated/rules.json";
import type { IEPRecord, PipelineStatusEvent, TeacherBrief } from "../src/lib/types/generated";
import type { Deadline, Finding, RegistryResponse } from "../src/lib/api/contracts";
import { RIVERSIDE_DEMO } from "../src/lib/riverside";

export const MOCK_RUN_ID = "ef45509a-2569-5c0d-ae9e-0c9838d2025a";
export const MOCK_IEP_VERSION_ID = "9e9d11d5-5684-5aa1-b93d-a09a3fbc87bb";

export const riversideRecord = iepRecord as IEPRecord;

const timestamp = (seconds: number): string => `2026-11-13T16:00:${String(seconds).padStart(2, "0")}Z`;

export const pipelineEvents: PipelineStatusEvent[] = [
  event(1, "ingest", "Ingest Agent", "running", "Opening the four-page Riverside IEP and preparing each page.", 0.15, null, 0),
  event(2, "ocr_page_1", "Source Page 1", "running", "Reading identity and eligibility fields from page 1.", 0.4, "ingest", 1),
  event(3, "ocr_page_2", "Source Page 2", "running", "Reading accommodations and their stated scope from page 2.", 0.4, "ingest", 2),
  event(4, "ingest", "Ingest Agent", "done", "Prepared 4 source pages with OCR and IEP preflight.", 1, null, 3),
  event(5, "extract", "Extraction Agent", "running", "Structuring fields while preserving page and quote evidence.", 0.55, null, 4),
  event(6, "extract", "Extraction Agent", "done", "Validated the source-grounded IEPRecord contract.", 1, null, 5),
  event(7, "confidence_gate", "Confidence Gate", "running", "Checking every field and scope reference against review thresholds.", 0.7, null, 6),
  event(8, "confidence_gate", "Confidence Gate", "needs_review", "2 fields need your review before legal duties can be derived.", 1, null, 7),
  event(9, "human_approval", "Case Manager Review", "needs_review", "Awaiting Priya's review of the extracted values and exact source evidence.", null, null, 8),
  event(10, "human_approval", "Case Manager Review", "done", "Approved. The verified record is ready for deterministic rules.", 1, null, 9),
  event(11, "rules", "Rules Engine", "running", "Applying the cited registry to the approved IEP—no model calls.", 0.65, null, 10),
  event(12, "rules", "Rules Engine", "done", "Derived teacher responsibilities and compliance findings in canonical order.", 1, null, 11),
];

function event(
  seq: number,
  stage: string,
  agentLabel: string,
  state: PipelineStatusEvent["state"],
  detail: string,
  progress: number | null,
  parentStage: string | null,
  seconds: number,
): PipelineStatusEvent {
  return {
    run_id: MOCK_RUN_ID,
    seq,
    stage,
    agent_label: agentLabel,
    state,
    detail,
    progress,
    parent_stage: parentStage,
    ts: timestamp(seconds),
  };
}

export const findings: Finding[] = [
  {
    id: "388dc804-9d8f-52dc-95b2-88884749c76f",
    rule_id: "teacher-informed-accommodations",
    citation: "34 CFR §300.323(d)(2)(ii)",
    finding_type: "partial_class_confirmation",
    severity: "warning",
    student_ref: "RIV-1001",
    iep_record_version_id: MOCK_IEP_VERSION_ID,
    detected_on: "2026-11-13",
    title: "Extended time — confirmed in 3 of 6 classes",
    detail: "Extended time is confirmed in 3 of 6 classes; 3 classes remain unconfirmed.",
    related_refs: { confirmed_classes: ["ENG-101", "MTH-101", "BIO-101"], unconfirmed_classes: ["HIS-101", "PE-101", "ART-101"] },
    measurements: { confirmed_classes: 3, total_classes: 6 },
    status: "open",
  },
  {
    id: "413933a1-972b-5f42-b390-a8a61561ce10",
    rule_id: "progress-report-cadence",
    citation: "34 CFR §300.320(a)(3)",
    finding_type: "progress_signal_conflict",
    severity: "warning",
    student_ref: "RIV-1001",
    iep_record_version_id: MOCK_IEP_VERSION_ID,
    detected_on: "2026-11-13",
    title: "Goal 2 evidence needs review",
    detail: "Coursework shows 40% mastery while the latest teacher check-in says “doing well.”",
    related_refs: { goal: riversideRecord.goals[1]?.id ?? "goal-2" },
    measurements: { coursework_mastery: 40 },
    status: "open",
  },
  {
    id: "7c152754-a063-5a60-a9dc-fd2ca9804326",
    rule_id: "services-statement",
    citation: "34 CFR §300.320(a)(4)",
    finding_type: "service_minute_variance",
    severity: "warning",
    student_ref: "RIV-1002",
    iep_record_version_id: "867af96f-75dc-5afc-acab-66ec09add530",
    detected_on: "2026-11-13",
    title: "Specialized instruction is 20 minutes under mandate",
    detail: "130 of 150 required weekly minutes were delivered.",
    related_refs: { service: "Specialized academic instruction" },
    measurements: { required_minutes: 150, delivered_minutes: 130, variance_minutes: -20 },
    status: "open",
  },
];

export const deadlines: Deadline[] = [
  {
    id: "3318f749-3cd8-5fca-a031-ae27b755c35c",
    rule_id: "annual-review",
    citation: "34 CFR §300.324(b)(1)(i)",
    student_ref: "RIV-1004",
    iep_record_version_id: "9872d066-524d-5cb5-bdf4-44167f059998",
    source_kind: "iep_record",
    source_ref: "a26fe4ad-8da5-5b78-a922-83d496766313",
    legal_due_on: "2026-10-30",
    action_due_on: "2026-10-30",
    warning_30_on: "2026-09-18",
    warning_14_on: "2026-10-09",
    warning_3_on: "2026-10-27",
    status: "overdue",
    description: "Annual IEP review",
  },
  {
    id: "f9a23b42-5975-5ef6-a6db-c027b42c16af",
    rule_id: "annual-review",
    citation: "34 CFR §300.324(b)(1)(i)",
    student_ref: "RIV-1005",
    iep_record_version_id: "1896e1d1-4981-52fc-801c-dc54d15e4e44",
    source_kind: "iep_record",
    source_ref: "df1378fa-8bca-5291-ab34-01839af80e6a",
    legal_due_on: "2026-11-11",
    action_due_on: "2026-11-10",
    warning_30_on: "2026-09-30",
    warning_14_on: "2026-10-21",
    warning_3_on: "2026-11-06",
    status: "overdue",
    description: "Annual IEP review",
  },
  {
    id: "a4529732-e393-5bf4-bfdb-69220408cadf",
    rule_id: "triennial-reevaluation",
    citation: "34 CFR §300.303(b)(2)",
    student_ref: "RIV-1003",
    iep_record_version_id: "1329d2f5-c0e5-5dc8-892d-830491a6481a",
    source_kind: "iep_record",
    source_ref: "cc6f8807-bebd-5946-902b-aae89b2d962c",
    legal_due_on: "2026-11-20",
    action_due_on: "2026-11-20",
    warning_30_on: "2026-10-09",
    warning_14_on: "2026-10-30",
    warning_3_on: "2026-11-17",
    status: "upcoming",
    description: "Triennial reevaluation",
  },
  {
    id: "48b1479a-0096-5b9b-b08a-7b7638465b54",
    rule_id: "annual-review",
    citation: "34 CFR §300.324(b)(1)(i)",
    student_ref: "RIV-1008",
    iep_record_version_id: "6535cb6e-68de-5dbf-a97d-6e9ff3a3ea40",
    source_kind: "iep_record",
    source_ref: "28a8bf74-6d4b-5ea1-9c18-4cb92cd08f0f",
    legal_due_on: "2027-01-27",
    action_due_on: "2027-01-27",
    warning_30_on: "2026-12-09",
    warning_14_on: "2027-01-06",
    warning_3_on: "2027-01-22",
    status: "upcoming",
    description: "Annual IEP review",
  },
];

export const registry = generatedRegistry satisfies RegistryResponse;

export const teacherBrief: TeacherBrief = {
  brief_id: "708a9042-e5c8-5fcf-9bb0-c6ee3cd333a5",
  teacher_ref: RIVERSIDE_DEMO.teacher.ref,
  class_ref: RIVERSIDE_DEMO.classroom.ref,
  subject: "English",
  school_year: "2026-2027",
  generated_at: "2026-11-13T16:00:12Z",
  rules_version: registry.rules_version,
  status: "released",
  released_at: "2026-11-13T16:00:12Z",
  confirmed_at: null,
  flag_reason: null,
  responsibility: {
    text: "Provide each approved accommodation listed below in English.",
    citation: "34 CFR §300.323(d)(2)(ii)",
  },
  students: [
    {
      student_ref: RIVERSIDE_DEMO.student.ref,
      student_name: RIVERSIDE_DEMO.student.name,
      obligations: riversideRecord.accommodations.slice(0, 3).map((accommodation, index) => ({
        obligation_id: [
          "96cc3c4f-546c-532d-a635-c368e4a4c9fa",
          "6f1831a1-f081-5622-96b0-10c6d9746c42",
          "b107ab79-a385-5018-bb6b-cd11f4ead509",
        ][index]!,
        accommodation_id: accommodation.id,
        accommodation_text: accommodation.text,
        action_text: accommodation.text,
        practice_text: [
          "Add 50% to the scheduled test window and note the adjusted end time before the student begins.",
          "Offer the quieter side table or testing room without requiring the student to request it publicly.",
          "Enable the district text-to-speech tool for assigned readings and directions before class begins.",
        ][index]!,
        source_page: accommodation.source_page,
        source_quote: accommodation.source_quote,
        source_confidence: accommodation.confidence,
        rule_id: "teacher-informed-accommodations",
        citation: "34 CFR §300.323(d)(2)(ii)",
      })),
    },
  ],
};
