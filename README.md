# Bitcoin Fee Rate Prediction Project

This repository contains code, data, and results for forecasting Bitcoin transaction fees using various time-series modeling approaches. The models predict fee rates for the next 144 blocks (~24 hours) using cross-validation and test datasets.

In our paper ([arXiv:2502.01029](https://arxiv.org/abs/2502.01029)), we use only the **large dataset**, which spans from September 16, 2024, to December 15, 2024, and contains 11,809 records (~91 days). The **small dataset** follows the same structure and modeling setup but is not included in the paper. It is provided for exploration, and you are welcome to experiment with it.

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
- [Citation](#citation)

---

## Usage

### Data Preprocessing
1. Perform exploratory data analysis (EDA) on the **large dataset** using `EDA_real_time_larger.ipynb`.
2. Clean and preprocess the raw data using the provided scripts.

### Model Training
1. Open the relevant notebook in the `Models` directory (e.g., `SARIMAX.ipynb`).
2. Train models using the provided datasets (`train_set.csv`, `test_set.csv`).

### Evaluation
1. Evaluate cross-validation and test results stored in `Results_large_dataset/model_outputs`.
2. Use plots in `Results_large_dataset/plots` for visual analysis.

---

## Results Summary

### Best Performing Models:
- **SARIMAX**: Achieved the lowest MAE and RMSE in both cross-validation and test datasets.
- **Hybrid Model**: Performed comparably to SARIMAX with strong overall robustness.

### Deep Learning Models:
- **Temporal Fusion Transformer (TFT)**: Produced reasonable results but struggled with generalization.
- **Time2Vec + Attention**: Showed high prediction errors and limited adaptability.

For detailed results, refer to:
- `Results_large_dataset/model_outputs`: Numerical evaluation metrics.
- `Results_large_dataset/figures`: Visual comparisons of predictions.

---

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

---

## License
This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.

---

## Citation
If you use this work, please cite:

@misc{ma2025comprehensivemodelingapproachesforecasting,

      title={Comprehensive Modeling Approaches for Forecasting Bitcoin Transaction Fees: A Comparative Study}, 
      
      author={Jiangqin Ma and Erfan Mahmoudinia},
      
      year={2025},
      
      eprint={2502.01029},
      
      archivePrefix={arXiv},
      
      primaryClass={cs.LG},
      
      url={https://arxiv.org/abs/2502.01029}, 
}

