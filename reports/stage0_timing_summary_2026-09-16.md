# Stage 0C Internal Timing

These values come from GPU-synchronized wrappers around the pinned Protenix model. They cover model forward only; model load, input preprocessing, confidence-file serialization, and CIF writing are excluded.

| setting | n | model mean / median (s) | pairformer mean / median (s) | diffusion mean / median (s) | confidence mean / median (s) | pairformer fraction | diffusion fraction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| c1_s1 | 128 | 1.2122 / 0.9033 | 0.6658 / 0.4435 | 0.0370 / 0.0256 | 0.2926 / 0.1900 | 0.549 | 0.031 |
| c1_s5 | 128 | 0.6088 / 0.4151 | 0.3371 / 0.2112 | 0.0770 / 0.0701 | 0.1553 / 0.1011 | 0.554 | 0.127 |
| c4_s1 | 128 | 1.5075 / 0.9708 | 1.2955 / 0.8087 | 0.0190 / 0.0173 | 0.1544 / 0.1050 | 0.859 | 0.013 |
| c4_s5 | 128 | 1.5628 / 1.0172 | 1.2954 / 0.8084 | 0.0753 / 0.0704 | 0.1541 / 0.1023 | 0.829 | 0.048 |

The four settings used the same 128-target prefix of `temporal_dev_v1`; timing is diagnostic and is not a final throughput benchmark. The c1_s5, c4_s1, and c4_s5 jobs shared one A800 node, so their paired comparisons are the cleanest same-node timing comparison.

On that same node, c1_s5 -> c4_s5 increased median pairformer time by about 0.585 s and median model-forward time by about 0.587 s. c4_s1 -> c4_s5 increased median diffusion time by about 0.053 s while median pairformer time changed by about 0.002 s.
