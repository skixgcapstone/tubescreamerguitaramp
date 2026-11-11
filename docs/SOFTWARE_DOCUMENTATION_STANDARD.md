# Software Documentation Standard

Version: 1.0  
Effective date: 2026-09-03  
Owner: SKIXG software team

## 1. Purpose

This standard defines the required structure for SKIXG software documentation. It adapts the capstone course examples into a concise format that supports design reviews, implementation, verification, and final-report reuse.

## 2. Course Basis

The standard was derived from the course coding standard, functional specification, performance specification, test matrix, and final technical report examples in:

`/Users/gauravsdama/git/pallie/tamu courses/capstone/canvas_course_content/viewer/files`

The course material consistently separates measurable requirements, high-level design, implementation details, hardware/software integration, and verification evidence. Code should be readable, explicit, cohesive, minimally scoped, and organized into files smaller than 1,000 lines.

## 3. Required Document Sections

Every release document shall use the following numbered sections.

1. Document Control: version, status, owner, review date, and change history.
2. Purpose and Scope: intended capability, users, supported platform, and explicit exclusions.
3. System Context: hardware/software boundary and end-to-end signal flow.
4. Functional Requirements: uniquely identified, testable behavior using `SW-F-###` identifiers.
5. Performance Requirements: measurable limits using `SW-P-###` identifiers.
6. Architecture and Software Stack: module diagram, dependencies, processes, threads, and data ownership.
7. Module Design: responsibility, inputs, outputs, failure behavior, and hardware replacement point for each module.
8. Interfaces and Configuration: audio devices, file formats, GPIO/I2C boundaries, settings, and launch arguments.
9. Safety, Security, and Error Handling: safe states, validation, resource limits, dependency risks, and recovery.
10. Implementation Status: implemented, planned, deferred, and blocked work stated separately.
11. Verification and Traceability: each requirement mapped to a repeatable test and evidence location.
12. Deployment and Operations: installation, startup, shutdown, logs, diagnostics, and rollback.
13. Resource Budget: RAM, CPU, temperature, throttling, XRUN, and latency acceptance limits.
14. Open Decisions and Risks: unresolved choices with owner and due milestone.

## 4. Requirement Rules

- Each requirement shall describe one observable behavior or measurable constraint.
- Use `shall` for mandatory requirements and avoid subjective terms such as fast, simple, or user-friendly.
- State the verification method: inspection, analysis, demonstration, or test.
- Do not report simulated values as hardware measurements.
- Record changed or removed requirements in the change history instead of silently rewriting scope.

## 5. Verification Rules

The verification matrix shall include requirement ID, test ID, method, procedure summary, acceptance criterion, platform, status, and evidence path. A requirement is complete only when its evidence is recorded. Planned tests must be marked `Not run`; they must not be presented as passed.

## 6. Code Documentation Rules

- Prefer descriptive modules, classes, functions, and types over explanatory comments.
- Comments shall explain design intent, constraints, safety boundaries, or non-obvious reasoning.
- Public hardware and audio boundaries shall document units, ranges, channel count, and failure behavior.
- Keep UI, DSP, device I/O, configuration, and hardware control in separate cohesive modules.
- Use the standard library where it satisfies the requirement; every added dependency requires a documented purpose and deployment step.
- Update the architecture graph after code changes with `graphify update .`.

## 7. Change Process

Update the living software document in the same change that modifies requirements, module boundaries, dependencies, hardware assumptions, or verification results. Review the requirement table and test matrix before each software documentation draft and capstone design review.
