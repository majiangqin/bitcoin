# Bitcoin Fee Rate Prediction Project

This repository contains code, data, and results for forecasting Bitcoin transaction fees using various time-series modeling approaches. The models evaluate fee rate prediction for the next 144 blocks (~24 hours) using cross-validation and test datasets.

In the paper, we use only the **large dataset**, spanning from September 16, 2024, to December 15, 2024, comprising 11,809 records (approximately 91 days). The **small dataset** has the same data structure and modeling setup but is not included in the paper. It is provided for exploration purposes, and you are welcome to experiment with it freely.

## Table of Contents

- [Usage](#usage)
  - [Data Preprocessing](#data-preprocessing)
  - [Model Training](#model-training)
  - [Evaluation](#evaluation)
- [Results Summary](#results-summary)
  - [Best Performing Models](#best-performing-models)
  - [Deep Learning Models](#deep-learning-models)
- [Contributing](#contributing)
- [License](#license)
![Uploading Figma_u7r7chxH2e.gif…]()

---

## Usage

### Data Preprocessing
1. Perform EDA on the **large dataset** using `EDA_real_time_larger.ipynb`.
2. Clean the raw data using the provided scripts.

### Model Training
1. Open the relevant notebook in the `Models` directory (e.g., `SARIMAX.ipynb`).
2. Train models using the provided datasets (`train_set.csv`, `test_set.csv`).

### Evaluation
1. Evaluate cross-validation and test results stored in `Results_large dataset/model outputs`.
2. Use plots in `Results_large dataset/plots` for visual analysis.

---

## Results Summary

### Best Performing Models:
- **SARIMAX**: Achieved the lowest MAE and RMSE in cross-validation and test datasets.
- **Hybrid Model**: Comparable to SARIMAX with robust performance.

### Deep Learning Models:
- **TFT**: Reasonable results but struggled with generalization.
- **Time2Vec + Attention**: High prediction errors and limited adaptability.

Detailed results can be found in:
- `Results_large dataset/model outputs`: Numerical metrics.
- `Results_large dataset/plots`: Visual comparisons.

---

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

---

## License
This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.

