import type { Deadline, Finding } from "../../lib/api/contracts";

export interface DashboardSections {
  implementationGaps: Finding[];
  serviceVariances: Finding[];
  otherFindings: Finding[];
}

export function groupFindings(findings: readonly Finding[]): DashboardSections {
  return {
    implementationGaps: findings.filter((finding) => finding.finding_type === "partial_class_confirmation"),
    serviceVariances: findings.filter((finding) => finding.finding_type === "service_minute_variance"),
    otherFindings: findings.filter(
      (finding) =>
        finding.finding_type !== "partial_class_confirmation" &&
        finding.finding_type !== "service_minute_variance",
    ),
  };
}

export function orderedDeadlines(deadlines: readonly Deadline[]): Deadline[] {
  return [...deadlines].sort((left, right) => {
    const statusOrder = { overdue: 0, due: 1, upcoming: 2 } as const;
    return statusOrder[left.status] - statusOrder[right.status] || left.action_due_on.localeCompare(right.action_due_on);
  });
}

export function studentName(studentRef: string): string {
  const names: Record<string, string> = {
    "RIV-1001": "A. Sharma",
    "RIV-1002": "M. Bell",
    "RIV-1003": "S. Ramirez",
    "RIV-1004": "E. Thompson",
    "RIV-1005": "J. Williams",
    "RIV-1008": "N. Patel",
  };
  return names[studentRef] ?? studentRef;
}
