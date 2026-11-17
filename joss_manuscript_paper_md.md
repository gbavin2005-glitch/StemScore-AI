---
title: 'StemScore AI: An Integrated Artificial Intelligence Platform for Stem-Cell State Assessment, Differentiation Trajectory Analysis, and Microscopy-Based Morphological Characterization'
tags:
  - Python
  - bioinformatics
  - stem cells
  - gene expression
  - microscopy
  - differentiation trajectory
authors:
  - name: Sermaraja R
    affiliation: 1
  - name: Bavin G
    corresponding: true
    email: gbavin03@gmail.com
    affiliation: 1
affiliations:
  - name: Saveetha School of Engineering, Saveetha Institute of Medical and Technical Sciences (SIMATS), Saveetha University, Thandalam, Chennai-602105, India
    index: 1
date: 14 November 2026
bibliography: paper.bib
---

# Summary

In stem-cell research, there is a need for reliable means to assess molecular changes and cellular morphology during differentiation. However, having separate workflows to analyze gene-expression profiles, cell-state transitions, lineage-associated markers and microscopy images can be challenging for data interpretation. In this study, we introduce StemScore AI v7.1, an integrated artificial intelligence-based research platform, which is developed to support stem-cell data analysis. The platform includes gene-expression processing, quality control, scoring for pluripotency and proliferation, machine-learning cell-state prediction, differentiation trajectory analysis, lineage-marker assessment and microscopy-based morphological characterization [@calloni2013; @bock2011; @chu2023].

The main contribution of StemScore AI is the integration of these analytical functions into a single research workflow. Instead of a focus on gene-expression classification or image analysis, the platform incorporates molecular scoring, state prediction, trajectory visualization, lineage-associated analysis, microscopy measurements, quality control and result reporting. The goal of this integrated approach is to make the analysis of stem-cells more systematic and easier to interpret. At the same time, the different outputs need to be understood in relation to the evidence for them. The results of the RNA component evaluation are presented here, but the lineage-marker analysis and microscopy-based biological state classification require further independent validation to enable more robust predictive statements [@saelens2019; @lamanno2018].

# Statement of need

Stem cell research has emerged as an important area of biomedical science due to its relevance to developmental biology, disease modeling, drug discovery, tissue engineering and regenerative medicine. The reliability of these applications is not only based on keeping cells in controlled culture conditions but also on knowing the molecular and morphological changes that occur during differentiation. Stem cell differentiation is a dynamic process in which gene-expression patterns, cellular morphology and functional properties may change over time. But, it is difficult to interpret these changes consistently across different samples and experimental settings. Variability in gene-expression profiles, rates of differentiation and changes in cellular morphology can complicate assessments of stem-cell identity and developmental progression. Thus, reliable computational approaches are needed to enable systematic analysis and interpretation of stem cell research data [@thomson1998; @takahashi2006; @takahashi2007].

There are a variety of techniques for studying stem cells, but interpreting the results can be difficult. The time taken for differentiation alone does not always represent the true status of a cell population, since cells may progress at different rates. Likewise, the reliance on only a few marker genes may not be sufficient to capture the full scope of molecular changes occurring during differentiation. Microscopic analysis can provide useful visual information, however, the variability in image quality and subjectivity of interpretation may affect the consistency of the observations. Also gene expression analysis, cell state prediction, lineage assessment, and image analysis may be done using different tools and workflows. The independent management of these analyzes can complicate the comparison of results and the maintenance of a consistent approach across experiments [@calloni2013; @bock2011; @street2018].

# State of the field

Some of these challenges can be addressed through computational approaches and artificial intelligence. Existing computational tools address individual components of transcriptomic trajectory inference, single-cell expression analysis, and cellular image quantification [@trapnell2014; @haghverdi2016; @qiu2017; @street2018; @wolf2018; @stuart2019; @carpenter2006; @schneider2012; @schindelin2012; @mcquin2018]. Gene-expression data can be used to generate quantitative scores, to predict broad cell states and to investigate changes between differentiation time points. By visualizing these changes as trajectories, more information can be gathered than by examining single samples. Tools for gene contribution and marker analysis can also help researchers to understand patterns relating to model outputs. At the same time, quantitative microscopy can be used to quantify image quality and morphological features rather than only visual inspection. However, the effectiveness of these methods depends on the quality of the data, proper preprocessing, reliable reference labels, and correct validation. Thus, it is worthwhile to combine several analytical functions in one application, but each function has to be validated for accuracy separately [@fawcett2006; @chicco2020; @carpenter2006; @tokunaga2014].

# Software design and architecture

StemScore AI was developed as a computational research platform to support the analysis of stem-cell gene-expression data and microscopy images (Figure 1). The development approach focused on making these analyses accessible through a common workflow while keeping the outputs of individual modules distinguishable. Gene-expression and microscopy data were analysed separately because a validated method for combining both data types into a single biological prediction was not yet established. The platform was therefore designed as a research-support tool rather than a clinical diagnostic system.

![Main interface of StemScore AI v7.1 showing the integrated GEO analysis, gene-expression file, results, gene-contribution, lineage-analysis and microscopy modules.](figures/figure1.png)

## Gene-Expression Data Processing and Scoring

The RNA-analysis module accepts gene-expression matrices in which rows represent genes and columns represent samples, supporting local files or publicly available expression datasets from NCBI GEO [@edgar2002; @clough2024; @fawcett2006; @saito2015]. The platform uses rank-based normalization to avoid dependence on the differences in numerical expression scales. For each sample, the genes are ranked based on their expression values, and the relative ranks are converted to percentile-like values. Rank normalization, however, does not remove all batch effects or differences arising from experimental protocols [@johnson2007; @leek2010; @chicco2020; @varoquaux2018]. The software also reports gene and model-feature coverage.

* **Pluripotency-Associated Scoring:** Assessed using a predefined panel of eight genes (`NANOG`, `SOX2`, `LIN28A`, `DPPA4`, `TDGF1`, `DNMT3B`, `ZFP42`, and `GDF3`) [@boyer2005; @loh2006; @chambers2007; @calloni2013]. The documented scoring method calculates the average rank of the eight markers and subsequently rescales the score using reference values derived from the model's pluripotent and differentiated training groups. If a required marker is missing, the score is reported as unavailable, and not calculated from an incomplete panel.
* **Proliferation-Associated Scoring:** Calculated separately using twelve genes (`MCM2`, `MCM3`, `MCM4`, `MCM5`, `MCM6`, `MCM7`, `PCNA`, `MKI67`, `TOP2A`, `CCNB1`, `CDK1`, and `ORC1`) representing components associated with DNA replication and cell-cycle activity [@boyer2005; @loh2006; @calloni2013]. The proliferation and pluripotency scores are retained as separate outputs because high proliferation-associated expression does not, by itself, establish pluripotent identity.

## Machine-Learning-Based Cell-State Prediction and Trajectory Analysis

StemScore AI utilizes a pre-trained machine-learning classifier implemented in Python [@pedregosa2011] to predict three cell states: `Pluripotent`, `Progenitor`, and `Differentiated` (Figure 2). The confidence is defined as the maximum predicted probability of class, with a fixed confidence threshold of `0.60`. Samples with confidence `< 0.60` are given the output label `"Uncertain"` as prediction abstention, while all three class probabilities are kept for interpretation [@trapnell2014; @haghverdi2016; @qiu2017].

The trajectory module examines changes in pluripotency-associated scores across samples collected at different stages of differentiation and calculates a descriptive $t_{50}$ value, defined as the point at which the score reaches half of the difference between its starting and ending values [@edgar2002; @clough2024; @leek2010].

## Lineage-Marker Assessment and Microscopy Analysis

The lineage module includes marker panels for neural (`SOX1`, `PAX6`, `NES`, `TUBB3`, `MAP2`), cardiac (`NKX2-5`, `GATA4`, `TNNT2`), and hepatic (`SOX17`, `FOXA2`, `HNF4A`, `ALB`) differentiation to generate lineage-associated scores for exploratory comparison.

The microscopy module extracts image-quality and morphological features including image sharpness, foreground or structure fraction, candidate objects or colonies, area, circularity, solidity, eccentricity, and texture-related heterogeneity [@street2018; @wolf2018; @stuart2019]. These morphology outputs remain separate from RNA-based cell-state predictions in the current platform.

# Verification and exploratory evaluation

## Software Verification

The source code of StemScore AI was evaluated using Python syntax compilation, automated acceptance tests, and regression testing. The automated acceptance suite recorded 17 successful assertions and 3 successful marker-integrity regression assertions. A standalone Windows executable (`StemScoreAI_v7.1.exe`, 126,678,466 bytes) was built using PyInstaller, and functional checks confirmed application launch, GEO dataset upload, analysis execution, prediction and confidence display, and CSV and report exports [@saelens2019; @lamanno2018; @carpenter2006].

## Exploratory Gene-Expression and Challenge Evaluation

We tested analytical performance in selected gene-expression datasets including a hepatic differentiation time course (`GSE70741`), a 31-sample expression dataset, and a five-sample challenge dataset:

* **Hepatic Differentiation Time Course (`GSE70741`):** Across ten samples collected from day 0 to day 21, the pluripotency-associated score was strongly negatively correlated with differentiation time (Spearman's $\rho = -0.988$) with 65.15% model-feature coverage (Figure 3) [@edgar2002; @clough2024; @leek2010]. Because the classifier was refitted using stored training data containing only the shared model genes, this analysis is treated as exploratory rather than an independent evaluation of the original frozen classifier.
* **31-Sample Expression Output:** The predicted categories comprised 13 Differentiated samples, seven Pluripotent samples, four Progenitor samples, and seven Uncertain samples, with 90.2% reported model-gene coverage [@trapnell2014; @haghverdi2016; @qiu2017].
* **Five-Sample Challenge Evaluation:** Evaluated using a matrix of 26,255 genes (99.65% coverage of the 2,000 model features; 99.45% of the stored rank universe) across three fibroblast samples (`Healthy_Fib`, `LCPD1_Fib`, `LCPD2_Fib`) and two induced mesenchymal stromal cell samples (`Healthy_iMSC`, `LCPD2_iMSC`) using operational proxy labels. All five samples were predicted as Differentiated, yielding an accuracy of 60%, balanced accuracy of 50%, macro-F1 score of 0.375, and 0% sensitivity for the progenitor-like proxy group [@trapnell2014; @haghverdi2016; @qiu2017].

![StemScore AI cell-state prediction output for the ten GSE70741 time points, showing predicted state, model probabilities, confidence, pluripotency and proliferation scores, and model-feature coverage.](figures/figure3.png)

# Limitations and future work

Although StemScore AI integrates multiple analytical workflows, additional biological validation is needed to confirm its predictive reliability. Evaluation on the five-sample challenge revealed limitations in identifying progenitor-like samples, indicating a need for improved classifier performance and evaluation on larger independently annotated datasets. The confidence threshold of 0.60 still lacks statistical calibration, and the lineage-marker module needs further validation by experimental evidence. Likewise, the microscopy module currently provides exploratory morphological measurements that need to be assessed with expert-annotated images. Future work will involve improving the generalizability of classifiers, calibration of confidence, lineage assessment, and microscopy accuracy.

# Data and code availability

The source code of StemScore AI is publicly available through GitHub at `https://github.com/gbavin2005-glitch/StemScore-AI` [@wilkinson2016; @katz2021]. The version-specific source-code release (`v7.1.1`) has been archived in Zenodo and is accessible through the DOI `https://doi.org/10.5281/zenodo.23857303`. This release represents a preliminary public source-code snapshot. Model weights, microscopy reference images, and original training datasets are not included in the archived package. Independent software validation and complete reproducibility assessment are ongoing.

# Acknowledgements

The authors acknowledge the contributions of everyone who supported the development and refinement of the StemScore AI platform. The authors also acknowledge the publicly available gene-expression datasets used during software development and evaluation.

# References