# SATO: Strips as Tokens — Artist Mesh Generation with Native UV Segmentation

SATO는 3D mesh 생성을 "triangle strip"을 기본 단위로 하는 autoregressive sequence prediction 문제로 재구성한 framework로, 기존 vertex-coordinate 토큰화의 비효율을 깨고 artist 퀄리티의 edge flow와 structural regularity를 보존한다. 핵심 혁신은 (1) mesh를 zipper-like하게 자라나는 strip의 사슬로 직렬화하는 **strip-based tokenization**, (2) 같은 토큰 시퀀스를 stride σ=1/σ=2로 해석해 triangle/quad 어느 쪽으로도 디코딩하는 **통합 tri/quad 표현**, (3) UV island 경계를 토큰 시퀀스 내부에 직접 임베드하여 geometry와 UV chart partition을 동시 생성하는 **native UV segmentation**이다 ([raw/sato.pdf](../raw/sato.pdf), arXiv:2604.09132v1, 2026-04-10).

## 핵심 문제 인식

기존 autoregressive mesh generation(MeshAnythingV2, BPT, TreeMeshGPT, DeepMesh 등)의 한계:

1. **Vertex/triangle-level 토큰화의 비효율** — 각 face를 독립 토큰으로 내보내면 시퀀스가 지나치게 길어지고, transformer가 local edge-flow 규칙을 학습하기 어려움
2. **Artist mesh topology 와의 괴리** — 실제 작업자는 edge flow가 깨끗하고 quad 위주인 mesh를 만들지만, 생성 모델은 이 규칙성을 잃기 쉬움
3. **UV unwrapping이 post-processing** — geometry 생성 후 별도 파이프라인(xatlas 등)으로 UV island를 잘라야 하며, semantically meaningful한 분할 보장이 없음

## Method

### Strip-based Tokenization

고전 컴퓨터 그래픽스의 **triangle strip** 개념(각 새 삼각형이 이전 삼각형과 edge를 공유)을 생성 모델의 기본 단위로 재활용:

- **Deterministic greedy extraction**: lowest-coordinate-first로 seed face 선택 → edge-to-face adjacency를 따라 zipper-like growth
- 각 strip은 첫 face 이후 **단일 정점 추가(triangle, σ=1)** 또는 **정점 쌍 추가(quad, σ=2)** 만으로 확장
- Strip이 더 이상 자랄 수 없으면 특수 **strip transition token(C₁′)** 으로 끊고 다음 strip 시작

### Hierarchical 3-level Geometry Quantization

정점 좌표를 **512³ 등가 해상도**의 voxel grid로 양자화하되, 3단계(4³ / 8³ / 16³) prefix sharing 구조로 시퀀스 길이를 추가 압축:

- 동일 상위 voxel을 공유하는 정점들은 상위 prefix 토큰을 재사용
- Net compression ratio 0.283 (DeepMesh 0.330, BPT 0.228 대비 중간 — 단 의미 있는 단위인 strip을 보존한 상태)

### Stride-aware Unified Tri/Quad 표현

동일한 토큰 시퀀스를 σ=1로 디코딩하면 triangle mesh, σ=2로 디코딩하면 quad mesh가 됨:

- Quad 정점은 triangle strip과 consistent winding order가 되도록 재배열
- **Synergistic joint training**: 대규모 triangle 데이터(~1.11M meshes)로 구조적 prior 학습 → 소량 고품질 quad(120 meshes)로 fine-tune → 양방향 prior transfer

### Native UV Segmentation

Geometry 생성과 UV island partitioning을 **하나의 시퀀스 내부에서 동시에** 수행:

- 면(face)들을 UV island 별로 deterministic traversal 순서로 partition
- 확장된 vocabulary **C₁″ 토큰**으로 island 경계를 시퀀스 안에 직접 임베드 → 시퀀스 길이 증가 없음
- AR framework로서는 geometry + UV chart partition을 동시 생성하는 **최초** 사례

> **주의**: SATO가 생성하는 UV 정보는 **face → island ID 분할(partition)** 뿐이며, **per-vertex (u, v) 좌표 자체는 출력하지 않는다**. 실제 평면화는 분할된 각 island에 대해 LSCM/ABF/xatlas 같은 표준 parameterizer를 별도로 돌려서 얻는다. 따라서 논문이 보고하는 L2 Stretch / Area·Angle Distortion / Symmetric Dirichlet 지표는 "같은 parameterizer를 적용했을 때 SATO가 만든 chart 분할이 더 나은 unwrap을 낸다"는 의미로 읽어야 한다. SATO의 기여는 **cut placement / chart 결정**이고 평면화 알고리즘 자체가 아님.

### Architecture

```text
Point Cloud (mesh당 81,920 points 샘플링)
    ↓
Point Cloud Encoder  (1,024 condition tokens로 압축)
    ↓ cross-attn
Hourglass Transformer  ──▶ GPT-style AR Decoder
                                ↓
       token sequence (geometry + strip transition + UV island)
                                ↓
       stride-aware decode  →  tri mesh  or  quad mesh  (+ UV chart partition)
```

표준 next-token cross-entropy loss로 학습. 입력은 **항상 point cloud** — 즉, 임의의 dense/messy mesh가 있어도 일단 표면에서 81,920 points 샘플링해서 condition으로 넣고, 모델은 그 형상에 맞춰 새 strip 토큰 시퀀스를 처음부터 생성한다 (mesh-to-mesh 직접 변환이 아님).

### Training Strategy (3-stage)

1. **Pretraining** — Objaverse / ShapeNet / Thingi10K / Shutterstock licensed 데이터로 구성한 ~1.47M triangle mesh (UV 주석 ~1.11M)로 대규모 구조 prior 학습
2. **Fine-tuning** — 120개 고품질 quad mesh로 regularity 강화
3. **Bidirectional transfer** — σ=1/σ=2 해석을 모두 활용해 tri/quad 데이터의 prior를 양쪽으로 전파

## 주요 결과

### Triangle Mesh Generation (150-shape test set)

| Method | NC↑ | CD↓ | HD↓ | F1↑ |
|--------|-----|-----|-----|-----|
| DeepMesh | 0.859 | 0.020 | 0.120 | 0.240 |
| **SATO** | **0.909** | **0.009** | **0.117** | **0.503** |

→ 모든 reconstruction 지표에서 기존 SOTA(DeepMesh)를 상회. F1이 2배 이상 향상된 점은 strip-based 토큰이 local topology 예측에 강함을 시사.

### User Study (25 industry professionals)

- SATO **2.61** / DeepMesh 1.17 (높을수록 좋음, 랭킹 기반 점수)
- Artist가 실제로 선호하는 edge-flow·regularity 판단에서도 우세

### UV Segmentation

- **PartUV baseline 대비** L2 Stretch, Area Distortion, Angle Distortion, Symmetric Dirichlet energy 모두 낮음
- Geometry와 UV 분할이 **한 모델 안에서** 나오므로, 생성된 mesh를 바로 텍스처링 파이프라인에 투입 가능

## 프로젝트 관련성

SATO는 표면적으로는 general-purpose mesh generation 논문이지만, 다음 세 지점에서 본 프로젝트와 직접 맞닿아 있다.

### 1. UV island partitioning ↔ Garment panel

SATO의 **UV island**는 수학적으로 "3D 표면을 2D로 cut-and-unwrap한 semantic patch 집합"이며, 이는 [[Sewing-Pattern-Representation]]의 **panel 집합** 정의와 구조적으로 동형이다. SATO가 geometry와 island 분할을 한 AR 시퀀스에서 동시에 생성하는 전략은, 향후 **3D garment + sewing pattern을 단일 AR framework로 joint generate**하는 방향을 탐색할 때 직접적인 prior가 된다. [[PatternGPT]]가 .zprj로부터 분리된 pattern만 학습하는 현 구조와 상호 보완적.

### 2. Strip token vs Sewing token — 토크나이제이션 설계 참고

[[PatternGPT]]는 459 vocab의 완전 이산 토크나이제이션(BOS/PAT/LINE/BEZ/SEW + 256-bin 좌표 + scale 토큰)을 사용한다. SATO의 strip 토크나이제이션은 **기하학적 인접성(edge sharing)을 토큰 순서에 내재화**한다는 점에서 다른 설계 축을 보여주며, hierarchical prefix sharing과 strip-transition token 아이디어는 PatternGPT의 시퀀스 길이 압축이나 panel-간 연결 토큰화에 차용할 수 있는 패턴이다.

### 3. Artist-aligned topology와 CLO 워크플로우

SATO가 강조하는 "professional한 edge flow + quad 기반 regularity"는 [[CLO-Workflow-Integration]]이 요구하는 실무 수준 mesh 품질과 정렬된다. [[DiffGI]]/[[Omages]]/[[GIMDiffusion]] 계열이 pixel grid 기반의 continuous representation이라면, SATO는 **token-based discrete AR** 축의 대표 주자로서 [[Data-Representations-Comparison]]에 새 축을 추가한다.

## 다른 접근과의 비교

| 특성 | SATO | [[Omages]] | [[DiffGI]] | [[GIMDiffusion]] | [[PatternGPT]] |
|------|------|-----------|-----------|-----------------|---------------|
| Representation | Strip token sequence | 12ch 64×64 image | 32×32×4 TSDF+Pos | Multi-chart GIM | Sewing pattern token |
| Modeling | AR Transformer | DiT | Latent Diffusion (DiT+RF) | Collaborative Control | Causal Transformer |
| UV 처리 | **시퀀스 내 native 분할** | UV atlas 직접 사용 | UV chart 암시 보존 | UV chart 암시 보존 | N/A |
| Tri/Quad | **통합 (σ 해석)** | Triangle 중심 | Triangle (DMS) | Triangle | N/A |
| Garment 특화 | X (general) | X | △ (thin-shell) | X | O (pattern) |
| 주요 강점 | Artist-aligned topology + UV 동시 생성 | Geometry + PBR 통합 | Differentiable TSDF | 2D prior 재활용 | Discrete pattern 생성 |

## 적용 가능 해상도

이 계열(MeshGPT/MeshAnythingV2/BPT/TreeMeshGPT/DeepMesh/SATO)의 공통 특성으로, 시퀀스 길이가 곧 face count에 비례하므로 face/vertex 상한이 분명히 존재한다.

| 항목 | 수치 |
|------|------|
| 학습 데이터 face 범위 | **500 ~ 16,000** (hard filter) |
| Vertex/Face 비율 제약 | ≤ 1.0 (이상 시 "triangle soup"으로 제외) |
| 일반 closed manifold 기준 vertex 추정 | 약 **250 ~ 8,000** |
| Training context window | 9K tokens (truncated-window 전략) |
| Inference 시퀀스 | 9K 초과 가능 (논문 teapot 예시 = **20K tokens**) |
| 실용 sweet spot | **수천 face (~1K–5K)** 의 base mesh |

→ **수만 face 이상의 dense/simulation-ready mesh는 한 번에 생성하기 어렵다.** Garment 맥락에서 typical CLO simulation mesh는 30K~100K+ face라 **SATO 학습 분포의 1.5~6배**에 해당하므로, 현실적 활용은 다음 두 갈래:

- ✅ **Base/retopology shell 생성** (수천 face) — sketch/concept-level garment shape에 적합
- ✅ **다른 dense generator의 retopology 후처리** — [[DiffGI]] 등이 만든 dense surface를 point cloud로 샘플링 → SATO를 통과시켜 quad-dominant + UV partition된 base mesh 획득
- ❌ **End-to-end simulation-ready garment 직접 생성** — 면 수 부족, 별도 subdivision/dense remeshing 단계 필요

## Limitations & 향후 연결 지점

- **Resolution 상한** — 위 표 참조. AR sequence length 제약상 high-poly 직접 생성 불가
- **학습 데이터 규모의 비대칭** — quad 데이터는 120개에 불과. Garment 도메인에서는 CLO .zprj 기반 고품질 panel/quad 데이터를 자체 수집하면 fine-tune 단계를 더 두껍게 가져갈 여지가 있음
- **Thin-shell 특화 미검증** — 논문은 일반 3D object(Objaverse/ShapeNet) 위주. 의상처럼 극도로 얇은 non-manifold 구조에서의 거동은 실험되지 않음 — [[DiffGI]]의 TSDF/DMS와 병렬 평가 필요
- **Material/PBR 미지원** — geometry + UV 분할까지만 생성. [[Omages]]의 12-channel 통합 representation과 결합 가능성 존재
- **UV 좌표 자체는 미생성** — partition만 출력. 평면화는 표준 parameterizer 별도 적용 필요 (Method §Native UV Segmentation 주의 박스 참조)

## 출처

- Rui Xu, Dafei Qin, Kaichun Qiao, Qiujie Dong, Huaijin Pi, Qixuan Zhang, Longwen Zhang, Lan Xu, Jingyi Yu, Wenping Wang, Taku Komura. *Strips as Tokens: Artist Mesh Generation with Native UV Segmentation.* arXiv:2604.09132v1 [cs.CV], 2026-04-10.
- [SATO 논문 PDF](../raw/sato.pdf)
- 관련 wiki: [[Omages]], [[DiffGI]], [[GIMDiffusion]], [[PatternGPT]], [[Sewing-Pattern-Representation]], [[Data-Representations-Comparison]], [[End-to-End-Pipeline]]
