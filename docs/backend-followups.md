# Backend/schema follow-ups

## IEPRecord v1.2: require at least one applicability reference in JSON Schema

`packages/schemas/IEPRecord.json` requires the `applies_to_refs` property but its array
definition is missing `minItems: 1`. Add that keyword in the teammate-owned schema.

This is distinct from the conditional scope constraints intentionally enforced by the
Pydantic model (`all` exclusivity and normalized duplicate rejection). `minItems` is a
basic, widely supported structured-output keyword, belongs in JSON Schema, and signals to
the extraction model that at least one source-grounded reference is mandatory.

The synthetic generator and verifier enforce non-empty references locally until the schema
change lands. No backend or schema file was changed on `cc/02c-scope-refs`.
