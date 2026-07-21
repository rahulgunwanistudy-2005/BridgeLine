import district from "../../../../data/synthetic/district/district.json";

function required<T>(value: T | undefined, label: string): T {
  if (value === undefined) throw new Error(`Riverside demo fixture is missing ${label}.`);
  return value;
}

const teacher = required(district.teachers.find((item) => item.teacher_ref === "T-DELGADO"), "teacher T-DELGADO");
const student = required(district.students.find((item) => item.student_ref === "RIV-1001"), "student RIV-1001");
const classroom = required(district.classes.find((item) => item.class_ref === "ENG-101"), "class ENG-101");

export const RIVERSIDE_DEMO = {
  teacher: { ref: teacher.teacher_ref, name: teacher.display_name, role: teacher.role },
  student: { ref: student.student_ref, name: student.display_name, shortName: student.short_name },
  classroom: { ref: classroom.class_ref, name: classroom.name, period: classroom.period },
} as const;
