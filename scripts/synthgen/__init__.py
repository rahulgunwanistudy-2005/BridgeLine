"""cc/02 synthetic-dataset generation library for Riverside Demo School District.

Everything here is deterministic: stable UUIDs (uuid5), a fixed dataset epoch, and a
single fixed random seed. Regeneration is byte-stable so every harness metric is
reproducible. No real student data exists anywhere in this package or its output.
"""
