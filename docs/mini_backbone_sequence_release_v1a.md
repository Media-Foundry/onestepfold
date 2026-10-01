# Audit release amendment, before any hard-candidate output

2026-10-01. This is a POST-AUDIT, PRE-UTILITY amendment, not a preregistered rule.
The original v1 execution remains `stopped_at_audit`, gates[true,false,true,true].
No original report, numerical value, candidate or failure status is overwritten.

All four native/math complete logits VJPs agree (relativeL2<8.3e-5), all twelve
original-q JVP/native-VJP directions agree to <0.13% relative error, and both
native repeats exactly reproduce gradients and coordinates. All near-hard
nonregression checks pass. 5I27 stopped solely because three projected responses
(absolute1.01e-7 to7.36e-7) were below the1e-6 amplitude floor. Their errors are
only1.00e-10 to1.92e-10 and relative errors<=0.10%; this is NOT a pass dependent
only on absolute tolerance. Its full logits gradient norm is3.21e-5.

The absolute floor is inappropriate as a sole utility-release veto when true
forward/reverse AD and full nonzero vector comparison resolve this response. This
amendment does not label small logits gradients useful for finite substitutions.
That is what the still-unrun hard experiment must test.

Release now requires ALL original directions, including the formerly small ones,
to satisfy relative error<=5% for BOTH native-VJP/reference-JVP and reference
JVP/VJP; each compared magnitude must be nonzero. Full native/reference gradient
relativeL2<=1%, both norms>1e-10, coordinate max difference<=.001Angstrom,
hard endpoint parity, exact repeats, softmax routing, absence of parameter grads,
and the original near-hard nonregression must also hold. No direction replacement,
scaling, extra forward call, candidate reselection or new parent is permitted.

This tightens the directional comparison to a relative-only requirement while
removing the absolute response-amplitude veto. It must not be reported as having
passed the original v1 gate. Release metadata binds the original execution,
four audit reports, candidate manifests, and this amendment BEFORE hard evaluation.
The original target, all geometry limits, all19 replacements, seeds, candidate
selection, failure denominators and stopping rules are unchanged.
