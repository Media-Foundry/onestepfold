#!/usr/bin/env python3
"""HPC3 analysis of accepted endpoint outputs and the bounded gradient audit."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from fastglycan.paired_teacher_protocol import sha256, write_json

METRICS = ('all_atom_lddt', 'tm_score_ca_observed')


def vectors(rows, key, groups):
    values = {(r['group_id'], r['noise']): r['quality'][key] for r in rows}
    assert len(values) == len(rows) == len(groups) * 2
    x = np.array([[values[g, n] for n in (12345, 54321)] for g in groups]).mean(axis=1)
    assert np.isfinite(x).all()
    return x


def summaries(x, axis=-1):
    count = max(1, math.ceil(x.shape[axis] * .05))
    return {'mean': np.mean(x, axis=axis), 'p05': np.quantile(x, .05, axis=axis),
            'worst5_mean': np.sort(x, axis=axis)[..., :count].mean(axis=axis)}


def comparison(x, y):
    index = np.random.default_rng(20260926).integers(len(x), size=(5000, len(x)))
    sx, sy = summaries(x), summaries(y)
    bx, by = summaries(x[index]), summaries(y[index])
    return {k: {'delta': float(sx[k] - sy[k]), 'ci95': np.quantile(bx[k] - by[k], [.025, .975]).tolist()}
            for k in sx} | {'loss_gt_005_count': int(np.sum(x-y < -.05)), 'per_target_delta': (x-y).tolist()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    a = p.parse_args()
    root = a.root.resolve()
    lock = json.loads((root / 'lock.json').read_text())
    old = Path(lock['experiment_root'])
    reports, grads, hashes = {}, {}, {'lock.json': sha256(root / 'lock.json'), 'analysis_source': sha256(Path(__file__))}
    for arm in ('initial', 'gt_only', 'endpoint'):
        path = root / arm / 'report.json'
        g = json.loads(path.read_text())
        assert g['complete'] and g['optimizer_updates'] == 0 and g['weights_unchanged']
        assert g['lock_sha256'] == hashes['lock.json']
        assert g['checkpoint_sha256'] == lock['inputs'][lock['checkpoints'][arm]]
        wanted = {(r['group_id'], n) for r in lock['targets'] for n in lock['noises']}
        assert len(g['rows']) == 16 and {(r['group_id'], r['noise']) for r in g['rows']} == wanted
        if arm != 'initial':
            assert all(r['saved_prediction_replayed_exactly'] for r in g['rows'])
        grads[arm] = g
        hashes[str(path)] = sha256(path)
    for arm in ('gt_only', 'endpoint'):
        for name in ('report.json', 'history.json', 'training.jsonl', 'independent_validation_precision_v2.json'):
            path = old / arm / name
            hashes[str(path)] = sha256(path)
        report = json.loads((old / arm / 'report.json').read_text())
        qa = json.loads((old / arm / 'independent_validation_precision_v2.json').read_text())
        assert qa['complete'] and qa['gpu32_replay_exact'] and qa['report_sha256'] == sha256(old / arm / 'report.json')
        assert report['history_sha256'] == sha256(old / arm / 'history.json')
        assert report['training_sha256'] == sha256(old / arm / 'training.jsonl')
        reports[arm] = report
    groups = sorted({r['group_id'] for r in reports['gt_only']['last_validation']['rows']})
    assert len(groups) == 128
    values = {arm: {m: vectors(r['last_validation']['rows'], m, groups) for m in METRICS} for arm, r in reports.items()}
    result = {'complete': True, 'inputs_sha256': hashes, 'targets': groups, 'final_paired': {}, 'arms': {}, 'gradient': {}}
    lines = ['# 一步终点蒸馏：最终结论与目标梯度诊断（2026-09-26）', '',
        '原目标仍是 ESMC-600M、MSA-free、全重原子、c1/s1/K1。此次 16 次新增曝光的终点蒸馏尚未证明平均质量和尾部同时恢复；不能宣称已收敛，也不能据此排除所有蒸馏方法。', '',
        '原精度分离 QA 643804/643805 和报告 643806 已完成。GPU FP32 重放及独立 FP64 公式检查通过；原跨精度 1e-4 门槛失败仍保留。', '',
        '## 最终相同预算比较', '',
        '两个评估噪声先按目标取均值，未选最好 seed；不是独立训练重复。新增尾部分析以目标配对 bootstrap 5000 次、seed20260926，属探索性补充；与原报告 seed20260922 的区间会有小幅 Monte Carlo 差异。', '',
        '|指标|统计量|endpoint−GT|95% CI|', '|---|---|---:|---|']
    for m in METRICS:
        result['final_paired'][m] = comparison(values['endpoint'][m], values['gt_only'][m])
        for stat in ('mean', 'p05', 'worst5_mean'):
            v = result['final_paired'][m][stat]
            lines.append(f"|{m}|{stat}|{v['delta']:+.5f}|[{v['ci95'][0]:+.5f}, {v['ci95'][1]:+.5f}]|")
    joint = np.logical_or.reduce([values['endpoint'][m]-values['gt_only'][m] < -.05 for m in METRICS])
    result['joint_degradation_count'] = int(joint.sum())
    lines += ['', f'相对 GT-only，任一质量指标下降 >0.05：{joint.sum()}/128。此比例不是相对教师的退化比例。', '',
              '## 训练与开发集', '', '|学生|train512 lDDT|dev128 lDDT|train512 TM|dev128 TM|训练计时 GPU h|', '|---|---:|---:|---:|---:|---:|']
    histories = {}
    for arm, r in reports.items():
        train_groups = sorted({x['group_id'] for x in r['best_full_train']['rows']})
        assert len(train_groups) == 512
        trains = {m: float(vectors(r['best_full_train']['rows'], m, train_groups).mean()) for m in METRICS}
        logs = [json.loads(x) for x in (old / arm / 'training.jsonl').read_text().splitlines()]
        assert len(logs) == 8192
        last = logs[-512:]
        result['arms'][arm] = {'train': trains, 'validation': {m: float(v.mean()) for m,v in values[arm].items()},
            'training_gpu_hours': r['training_seconds']/3600,
            'last512_clip_fraction': float(np.mean([x['preclip_norm'] > 10 for x in last])),
            'last512_weighted_losses_mean': np.mean([x['weighted_losses'] for x in last],axis=0).tolist(),
            'last512_preclip_norm_median': float(np.median([x['preclip_norm'] for x in last]))}
        lines.append(f"|{arm}|{trains[METRICS[0]]:.4f}|{values[arm][METRICS[0]].mean():.4f}|{trains[METRICS[1]]:.4f}|{values[arm][METRICS[1]].mean():.4f}|{r['training_seconds']/3600:.3f}|")
        histories[arm] = json.loads((old / arm / 'history.json').read_text())
    teacher = json.loads((old / 'comparison.json').read_text())['teacher_reference']
    result['teacher_reference'] = teacher
    lines += ['', f"同指标 teacher c1_s1/c4_s2 mean lDDT：{teacher['c1_s1'][METRICS[0]]['mean']:.4f}/{teacher['c4_s2'][METRICS[0]]['mean']:.4f}。教师使用 ESM2-3B；这不能把权重、训练历史、PLM 与当前学生的差异归因于单一组件。",
              '训练计时不含验证和初始化，warm core 也不含 ESMC，不构成端到端速度验收。近同源开发集限制保留，冻结测试未使用。', '',
              '## 零更新梯度归因', '',
              '8 个 TRAIN probe 按预定长度位置选定，各两个固定噪声。以下中位数为先按目标平均两噪声后的 8 个值；cos<0 的比例按全部 16 次分别计算。比值已包含教师权重 0.1。', '',
              '|checkpoint|位置|教师/GT 范数比中位数|cos 中位数|cos<0 次数/16|', '|---|---|---:|---:|---:|']
    locations = ('parameters', 'raw_coordinate', 'articulated_coordinate', 'esmc_projection', 'pairformer', 'atom_decoder')
    for arm, g in grads.items():
        result['gradient'][arm] = {}
        for loc in locations:
            records = [r[loc] if loc in r else r['parameter_groups'][loc] for r in g['rows']]
            ratios = np.array([r['weighted_teacher_to_gt'] for r in records], dtype=float)
            cosine = np.array([r['cosine'] for r in records], dtype=float)
            assert np.isfinite(ratios).all() and np.isfinite(cosine).all()
            ratio8, cosine8 = ratios.reshape(8,2).mean(axis=1), cosine.reshape(8,2).mean(axis=1)
            item = {'median_target_mean_ratio': float(np.median(ratio8)), 'median_target_mean_cosine': float(np.median(cosine8)),
                    'negative_cosine_count': int((cosine < 0).sum()), 'gt_ascent_negative_sum_count': sum(r['gt_derivative_negative_sum'] > 0 for r in records),
                    'per_target_ratio': ratio8.tolist(), 'per_target_cosine': cosine8.tolist()}
            result['gradient'][arm][loc] = item
            lines.append(f"|{arm}|{loc}|{item['median_target_mean_ratio']:.4f}|{item['median_target_mean_cosine']:.4f}|{item['negative_cosine_count']}/16|")
    lines += ['', '两个最终 checkpoint 的这 32 个预测均与旧产物逐位一致；三个 checkpoint 检查前后权重相同，零 optimizer 更新。',
              '这里测的是裁剪前欧氏梯度，不是 AdamW 实际步向；局部夹角不能证明泛化因果。8 个训练目标不能代替总体随机种子重复。', '',
              '图与所有数值见同目录 figure.png、figure.pdf、analysis.json；原 pilot 产物及比较文件未改写。']
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1,3,figsize=(15,4), constrained_layout=True)
    for arm, history in histories.items():
        steps = [h['step'] for h in history]
        for view, style in [('validation','-'), ('train_probe','--')]:
            ys = [np.mean([r['quality'][METRICS[0]] for r in h[view]['rows']]) for h in history]
            axes[0].plot(steps,ys,style,label=arm+' '+view)
    axes[0].set(xlabel='Additional optimizer updates',ylabel='All-atom lDDT',title='Matched continuation budget')
    axes[0].legend(fontsize=7)
    axes[1].scatter(values['gt_only'][METRICS[0]], values['endpoint'][METRICS[0]],s=12,alpha=.7)
    axes[1].plot([.2,.65],[.2,.65],color='grey',lw=1)
    axes[1].set(xlabel='GT-only lDDT',ylabel='Endpoint lDDT',title='128 development targets; mean of 2 noises')
    for i,arm in enumerate(grads):
        vals=result['gradient'][arm]['parameters']['per_target_ratio']
        axes[2].scatter([i]*8,vals,label=arm,s=18)
    axes[2].set_xticks(range(3),list(grads))
    axes[2].set(ylabel='Weighted teacher / GT gradient norm',title='All trainable parameters; 8 TRAIN probes')
    fig.savefig(root/'figure.png',dpi=180);fig.savefig(root/'figure.pdf');plt.close(fig)
    result['plot_runtime'] = {'numpy': np.__version__, 'matplotlib': matplotlib.__version__}
    write_json(root / 'analysis.json', result)
    (root / 'report.md').write_text('\n'.join(lines)+'\n')
    print('Accepted diagnostic and supplementary quality report written',flush=True)


if __name__ == '__main__':
    main()
