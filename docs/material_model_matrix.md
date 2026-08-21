# SS316LN-N014 材料模型状态矩阵

日期: 2026-08-19
材料身份: SS316LN (N≈0.14 wt.%), 550–750°C, **AIR ONLY**
状态词: EXPERIMENTAL / FORMULA / ASSUMED / INTERPOLATED / EXTRAPOLATED / MISSING / CONVERTED

---

## 1. 模型版本

| 模型 | E(T) 来源 | 用途 |
|------|----------|------|
| **SS316LN_N014_EXP** | MAT-02 实测 (Pan2024 Table 2) | 实验参考;注明 N=0.13%、细晶 20μm |
| **SS316LN_N014_RCCMR** | RCC-MR 公式 E=201660−84.8·T(°C) | 工程基准(D 类公式,非实验) |

两个模型的其他参数完全相同(蠕变均为 MAT-05 空气数据),只有 E(T) 不同。

---

## 2. 温度 × 参数状态矩阵

### 2.1 SS316LN_N014_EXP

| T(°C) | E | ν | σy | 塑性曲线 | 蠕变(C,n) | 密度 | CTE | 导热 | 比热 |
|-------|----|----|-----|---------|----------|------|-----|------|------|
| 550 | **MISSING** | ASSUMED | **MISSING** | **MISSING** | **EXPERIMENTAL**(A) | MISSING | MISSING | MISSING | MISSING |
| 600 | **MISSING** | ASSUMED | **MISSING** | **MISSING** | **EXPERIMENTAL**(A) | MISSING | MISSING | MISSING | MISSING |
| 650 | **EXPERIMENTAL**(171 GPa, A) | ASSUMED | **EXPERIMENTAL**(227, A) | EXPERIMENTAL(C 数字化) | **EXPERIMENTAL**(A) | MISSING | MISSING | MISSING | MISSING |
| 700 | **EXPERIMENTAL**(141 GPa, A) | ASSUMED | **EXPERIMENTAL**(212, A) | EXPERIMENTAL(C) | **MISSING** | MISSING | MISSING | MISSING | MISSING |
| 750 | **EXPERIMENTAL**(119 GPa, A) | ASSUMED | **EXPERIMENTAL**(199, A) | EXPERIMENTAL(C) | **MISSING** | MISSING | MISSING | MISSING | MISSING |

### 2.2 SS316LN_N014_RCCMR

| T(°C) | E | ν | σy | 塑性曲线 | 蠕变(C,n) | 密度 | CTE | 导热 | 比热 |
|-------|----|----|-----|---------|----------|------|-----|------|------|
| 550 | **FORMULA**(155.02, D) | ASSUMED | **MISSING** | **MISSING** | **EXPERIMENTAL**(A) | MISSING | MISSING | MISSING | MISSING |
| 600 | **FORMULA**(150.78, D) | ASSUMED | **MISSING** | **MISSING** | **EXPERIMENTAL**(A) | MISSING | MISSING | MISSING | MISSING |
| 650 | **FORMULA**(146.54, D) | ASSUMED | **EXPERIMENTAL**(227, A) | EXPERIMENTAL(C) | **EXPERIMENTAL**(A) | MISSING | MISSING | MISSING | MISSING |
| 700 | **FORMULA**(142.30, D) | ASSUMED | **EXPERIMENTAL**(212, A) | EXPERIMENTAL(C) | **MISSING** | MISSING | MISSING | MISSING | MISSING |
| 750 | **FORMULA**超出适用范围(>700°C) | ASSUMED | **EXPERIMENTAL**(199, A) | EXPERIMENTAL(C) | **MISSING** | MISSING | MISSING | MISSING | MISSING |

> 注: RCC-MR 公式声明适用 20–700°C。**750°C 处公式为外推**(已标注,不伪装);EXP 模型 750°C 有实测 E=119 GPa。

---

## 3. 蠕变参数明细(两模型相同,均 AIR)

| T(°C) | C (%/h/MPaⁿ) | n | Abaqus A (s⁻¹/MPaⁿ) | 环境 | 状态 |
|-------|-------------|-----|----------------------|------|------|
| 550 | 2.79e-27 | 9.51 | 7.75e-32 | Air | EXPERIMENTAL (MAT-05) |
| 600 | 1.28e-24 | 9.04 | 3.56e-30 | Air | EXPERIMENTAL (MAT-05) |
| 650 | 8.46e-20 | 7.57 | 2.35e-25 | Air | EXPERIMENTAL (MAT-05) |
| 700 | — | — | — | — | **MISSING (DATA_REQUIRED)** |
| 750 | — | — | — | — | **MISSING (DATA_REQUIRED)** |

Abaqus A 值 = C/100/3600,标记 **CONVERTED**(由实验 C 换算,非新数据)。

---

## 4. 环境筛选记录

### 4.1 Air 可用数据 (use_for_model = YES)
- MAT-05 蠕变 C/n (550/600/650°C) — GaneshKumar 2013 Table 2
- MAT-02 空气断裂时间 (650/700/750°C) — Pan 2024 Table 3: 36.98 / 103.87 / 31.77 h
- MAT-02 E/σy/UTS/曲线 (650/700/750°C) — Pan 2024 Table 2/Fig.4

### 4.2 Sodium 排除数据 (use_for_model = NO, 记录于 excluded_sodium.csv)
- MAT-02 Norton n (氧饱和钠): 650°C n=24.20, 700°C n=9.38, 750°C n=17.56 (Pan 2024 Table 5)
- MAT-02 钠环境断裂时间: 650°C 13.52h, 700°C 33.31h, 750°C 19.04h (Pan 2024 Table 3)
- MAT-01 流动钠数据 (Ravi 2012): 因 N=0.06% 已在材料层排除

### 4.3 Environment = Unknown
- Schirra 1999 (MAT-03): 低应力 MCR 参考,测试环境未明确标注 → use_for_model = NO
- 未明确标注环境的任何数据:一律 UNKNOWN + use_for_model = NO

---

## 5. 关键声明

1. ν=0.30 为 **ASSUMED**(5 篇文献均未提供),非实验值;
2. E(T) 两套独立,不混合;
3. 550/600°C 屈服强度 **MISSING**,禁止插值(除非用户单独批准);
4. 塑性模型为 **elastic-perfectly-plastic benchmark**(简化模型),非完整真实本构;
5. 密度/CTE/导热/比热 **MISSING** → 当前仅 mechanical benchmark,不做真实热-力耦合;
6. 所有 sodium 数据严格排除,不参与任何 Abaqus 材料卡。
