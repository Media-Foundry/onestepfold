# Mini multi-reference editor: automatic terminal audit

All eight fixed runs and independent audits complete: **True**.
Reused development data; no automatic promotion or experimental-accuracy claim.

| Run | Stratum | Parent mean rho | Top1 / sites | Raw old-select/new regret | Max local RMSD A | Exact pass-to-fail |
|---|---|---:|---:|---:|---:|---:|
| n15_direct_global_272001/reference_only | dev_new_site | 0.183041 | 0/3 | 0.119167 | 6.2685 | 8 |
| n15_direct_global_272001/16416 | dev_new_site | 0.197661 | 0/3 | 0.136343 | 6.4436 | 14 |
| n15_direct_global_272001/reference_only | dev_unseen_protein | 0.152437 | 1/18 | 0.232504 | 6.1431 | 60 |
| n15_direct_global_272001/16416 | dev_unseen_protein | 0.034405 | 0/18 | 0.247365 | 6.1481 | 71 |
| n15_direct_global_272001/reference_only | train | 0.350058 | 8/27 | 0.155480 | 4.6690 | 55 |
| n15_direct_global_272001/16416 | train | 0.737076 | 13/27 | 0.044547 | 2.2617 | 41 |
| n15_direct_global_272003/reference_only | dev_new_site | 0.183041 | 0/3 | 0.119167 | 6.2685 | 8 |
| n15_direct_global_272003/16416 | dev_new_site | 0.205848 | 1/3 | 0.136343 | 6.3274 | 18 |
| n15_direct_global_272003/reference_only | dev_unseen_protein | 0.152437 | 1/18 | 0.232504 | 6.1431 | 60 |
| n15_direct_global_272003/16416 | dev_unseen_protein | 0.166667 | 2/18 | 0.332196 | 6.1007 | 67 |
| n15_direct_global_272003/reference_only | train | 0.350058 | 8/27 | 0.155480 | 4.6690 | 55 |
| n15_direct_global_272003/16416 | train | 0.719474 | 14/27 | 0.045643 | 2.2704 | 53 |
| n15_workspace_272001/reference_only | dev_new_site | 0.183041 | 0/3 | 0.119167 | 6.2685 | 8 |
| n15_workspace_272001/16416 | dev_new_site | 0.128655 | 0/3 | 0.101142 | 6.1869 | 16 |
| n15_workspace_272001/reference_only | dev_unseen_protein | 0.152437 | 1/18 | 0.232504 | 6.1431 | 60 |
| n15_workspace_272001/16416 | dev_unseen_protein | 0.117641 | 2/18 | 0.225584 | 6.1356 | 55 |
| n15_workspace_272001/reference_only | train | 0.350058 | 8/27 | 0.155480 | 4.6690 | 55 |
| n15_workspace_272001/16416 | train | 0.577427 | 9/27 | 0.036944 | 3.0198 | 38 |
| n15_workspace_272003/reference_only | dev_new_site | 0.183041 | 0/3 | 0.119167 | 6.2685 | 8 |
| n15_workspace_272003/16416 | dev_new_site | 0.195906 | 0/3 | 0.115777 | 6.4430 | 17 |
| n15_workspace_272003/reference_only | dev_unseen_protein | 0.152437 | 1/18 | 0.232504 | 6.1431 | 60 |
| n15_workspace_272003/16416 | dev_unseen_protein | -0.023489 | 1/18 | 0.174877 | 6.2346 | 88 |
| n15_workspace_272003/reference_only | train | 0.350058 | 8/27 | 0.155480 | 4.6690 | 55 |
| n15_workspace_272003/16416 | train | 0.671988 | 13/27 | 0.039494 | 3.0292 | 39 |
| n3_direct_global_272001/reference_only | dev_new_site | -0.366667 | 0/1 | 0.202235 | 6.2685 | 8 |
| n3_direct_global_272001/3040 | dev_new_site | 0.252632 | 0/1 | 0.202235 | 6.5841 | 8 |
| n3_direct_global_272001/reference_only | dev_transition_parent_unseen_n3_seen_n15 | 0.457895 | 0/2 | 0.077633 | 5.4450 | 0 |
| n3_direct_global_272001/3040 | dev_transition_parent_unseen_n3_seen_n15 | 0.373684 | 0/2 | 0.471265 | 5.7346 | 3 |
| n3_direct_global_272001/reference_only | dev_unseen_protein | 0.152437 | 1/18 | 0.232504 | 6.1431 | 60 |
| n3_direct_global_272001/3040 | dev_unseen_protein | 0.045906 | 1/18 | 0.064164 | 7.0889 | 101 |
| n3_direct_global_272001/reference_only | expansion_sites_not_trained_n3 | 0.392763 | 6/22 | 0.185408 | 4.6690 | 49 |
| n3_direct_global_272001/3040 | expansion_sites_not_trained_n3 | 0.071418 | 2/22 | 0.085350 | 4.9137 | 91 |
| n3_direct_global_272001/reference_only | train | 0.179240 | 2/5 | 0.035768 | 3.1516 | 6 |
| n3_direct_global_272001/3040 | train | 0.760234 | 2/5 | 0.035654 | 1.6684 | 14 |
| n3_direct_global_272003/reference_only | dev_new_site | -0.366667 | 0/1 | 0.202235 | 6.2685 | 8 |
| n3_direct_global_272003/3040 | dev_new_site | -0.198246 | 0/1 | 0.330667 | 6.6716 | 10 |
| n3_direct_global_272003/reference_only | dev_transition_parent_unseen_n3_seen_n15 | 0.457895 | 0/2 | 0.077633 | 5.4450 | 0 |
| n3_direct_global_272003/3040 | dev_transition_parent_unseen_n3_seen_n15 | 0.294737 | 0/2 | 0.035921 | 5.3265 | 3 |
| n3_direct_global_272003/reference_only | dev_unseen_protein | 0.152437 | 1/18 | 0.232504 | 6.1431 | 60 |
| n3_direct_global_272003/3040 | dev_unseen_protein | 0.094639 | 1/18 | 0.180924 | 6.4640 | 110 |
| n3_direct_global_272003/reference_only | expansion_sites_not_trained_n3 | 0.392763 | 6/22 | 0.185408 | 4.6690 | 49 |
| n3_direct_global_272003/3040 | expansion_sites_not_trained_n3 | 0.218202 | 6/22 | 0.141212 | 7.9020 | 69 |
| n3_direct_global_272003/reference_only | train | 0.179240 | 2/5 | 0.035768 | 3.1516 | 6 |
| n3_direct_global_272003/3040 | train | 0.780702 | 1/5 | 0.040916 | 2.2628 | 4 |
| n3_workspace_272001/reference_only | dev_new_site | -0.366667 | 0/1 | 0.202235 | 6.2685 | 8 |
| n3_workspace_272001/3040 | dev_new_site | 0.059649 | 0/1 | 0.000000 | 5.8325 | 9 |
| n3_workspace_272001/reference_only | dev_transition_parent_unseen_n3_seen_n15 | 0.457895 | 0/2 | 0.077633 | 5.4450 | 0 |
| n3_workspace_272001/3040 | dev_transition_parent_unseen_n3_seen_n15 | 0.341228 | 0/2 | 0.035129 | 5.3821 | 5 |
| n3_workspace_272001/reference_only | dev_unseen_protein | 0.152437 | 1/18 | 0.232504 | 6.1431 | 60 |
| n3_workspace_272001/3040 | dev_unseen_protein | -0.008869 | 0/18 | 0.215173 | 6.5672 | 101 |
| n3_workspace_272001/reference_only | expansion_sites_not_trained_n3 | 0.392763 | 6/22 | 0.185408 | 4.6690 | 49 |
| n3_workspace_272001/3040 | expansion_sites_not_trained_n3 | 0.142836 | 3/22 | 0.165878 | 5.3083 | 68 |
| n3_workspace_272001/reference_only | train | 0.179240 | 2/5 | 0.035768 | 3.1516 | 6 |
| n3_workspace_272001/3040 | train | 0.497076 | 2/5 | 0.038381 | 3.0024 | 21 |
| n3_workspace_272003/reference_only | dev_new_site | -0.366667 | 0/1 | 0.202235 | 6.2685 | 8 |
| n3_workspace_272003/3040 | dev_new_site | 0.317544 | 0/1 | 0.117075 | 6.1935 | 11 |
| n3_workspace_272003/reference_only | dev_transition_parent_unseen_n3_seen_n15 | 0.457895 | 0/2 | 0.077633 | 5.4450 | 0 |
| n3_workspace_272003/3040 | dev_transition_parent_unseen_n3_seen_n15 | 0.471930 | 0/2 | 0.064278 | 5.4732 | 12 |
| n3_workspace_272003/reference_only | dev_unseen_protein | 0.152437 | 1/18 | 0.232504 | 6.1431 | 60 |
| n3_workspace_272003/3040 | dev_unseen_protein | 0.024464 | 1/18 | 0.164059 | 6.2922 | 105 |
| n3_workspace_272003/reference_only | expansion_sites_not_trained_n3 | 0.392763 | 6/22 | 0.185408 | 4.6690 | 49 |
| n3_workspace_272003/3040 | expansion_sites_not_trained_n3 | 0.097661 | 3/22 | 0.196792 | 18.0388 | 83 |
| n3_workspace_272003/reference_only | train | 0.179240 | 2/5 | 0.035768 | 3.1516 | 6 |
| n3_workspace_272003/3040 | train | 0.631579 | 1/5 | 0.038142 | 1.6324 | 16 |

See per-run scores.json.gz for every checkpoint, candidate/noise, geometry transition,
continuous checked volumes, distance response and parent bootstrap contrast.
A stopped or failed seed remains in finalizer.json; it is not replaced.
Component timing excludes reference ESM/C4 preparation and is not an end-to-end speedup.
