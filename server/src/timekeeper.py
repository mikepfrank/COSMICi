#|******************************************************************************
#|                              START OF FILE
#|******************************************************************************
#|
#|      FILE NAME:  timekeeper.py               [python module source file]
#|
#|      DESCRIPTION:
#|
#|          This file defines a worker thread class Timekeeper, an
#|          instance of which is the primary entity responsible for
#|          inferring and keeping track of absolute times in the
#|          COSMICi system.
#|
#|          This involves several major tasks:
#|
#|              1.  Maintaining a database of all time-related data
#|                      from the start of each run.  This information
#|                      should be maintained persistently in an easily-
#|                      queried form to support offline analysis,
#|                      perhaps using a back-end consisting of a
#|                      simple standard RDBMS system like MySQL.
#|
#|              2.  Calculating & maintaining other information needed
#|                      to map raw data to absolute event times.  For
#|                      example, the individual PPS edge crossing times
#|                      in terms of the 750 Mcps counter values can be
#|                      used as raw data points for fitting a model
#|                      curve for mapping arbitrary counter values to
#|                      real times.
#|
#|              3.  Displaying, for diagnostic purposes, real-time
#|                      graphs of the raw data and inferred curves for
#|                      item #2.
#|
#|      REVISION HISTORY:
#|
#|          v0.0, 3/12/12 (MPF) - Wrote file header including description.
#|
#|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
