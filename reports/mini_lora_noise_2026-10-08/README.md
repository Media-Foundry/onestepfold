# Mini LoRA noise control launch evidence

Immutable protocol: ../../docs/mini_lora_noise_v1.md. Remote lora_noise_v1_20261008.
Both seed preflights passed: fixedT37A two-noise zero-state replay; each four
serial/DDP mixed-noise gradient/update comparisons. All eight updated parameter
comparisons bitwise equal; maximum gradient difference1.401298464324817e-44.
Eight discarded updates, no trained outcome selection.20focusedlocaltests pass.
Controller snapshot shows first paired single/dual runs started; second seed
queued with reversed device-pair assignment. Only step0 initialization reused;
all four training runs fresh. No quality results or promotion yet.
manifest.json verifies every copied remote artifact. noise_lock.json records
1128 frozen code-file hashes, protocol and original step0 checkpoint hashes.
This is a launch snapshot; controller fields are not live progress.
