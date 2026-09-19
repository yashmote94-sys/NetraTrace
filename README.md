\# NetraTrace



\## AI-Powered Diabetic Retinopathy Screening System



NetraTrace is an AI-based web application designed to assist in diabetic retinopathy screening from retinal fundus images.



\### Features



\- AI-based diabetic retinopathy classification

\- Five-stage DR classification

\- Fundus image validation

\- ResNet18-based deep learning

\- Ordinal classification

\- Test-Time Augmentation (TTA)

\- Confidence and probability analysis

\- Grad-CAM explainability

\- Patient management

\- Screening history

\- Referral management

\- Follow-up management

\- SQLite database

\- Streamlit web interface



\### DR Classification



| Grade | Classification |

|---|---|

| 0 | No DR |

| 1 | Mild NPDR |

| 2 | Moderate NPDR |

| 3 | Severe NPDR |

| 4 | Proliferative DR |



\### Technology Stack



\- Python

\- Streamlit

\- PyTorch

\- torchvision

\- OpenCV

\- PIL

\- NumPy

\- SQLite

\- ResNet18

\- Grad-CAM



\### Project Structure



```text

NetraTrace/

├── app.py

├── database.py

├── theme.py

├── README.md

├── requirements.txt

│

├── model/

│   ├── best\_resnet18\_ordinal\_v2.pth

│   ├── fundus\_validator\_resnet18\_v2.pth

│   └── gradcam.py

│

└── screens/

&#x20;   ├── dashboard.py

&#x20;   ├── followups.py

&#x20;   ├── history.py

&#x20;   ├── patients.py

&#x20;   ├── referrals.py

&#x20;   ├── results.py

&#x20;   └── screening.py

