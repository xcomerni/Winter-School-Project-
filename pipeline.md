---
## Pipeline overview

```mermaid

flowchart TB
 subgraph RAW["<b>Raw data</b>"]
    direction TB
        R_M["<b>MOLA </b><br>DTM <br>profiles"]
        R_C["<b>CRISM </b><br>cubes<br>BD1900 / BD2210 / D2300"]
        R_T["<b>THEMIS</b> <br>images<br>multiple LST times"]
  end
 subgraph MOLA_PIPE["<b>MOLA pipeline</b>"]
    direction TB
        M_proc["<b>Pre-processing</b><br>projection, resampling, 100×100 grid"]
        M_feat["<b>Feature extraction</b><br>slope, roughness"]
        M_dec["<b>Decision criteria</b><br>slope &lt; 10° and hazard flags"]
        M_out["<b>Feature table</b><br>per grid cell"]
  end
 subgraph CRISM_PIPE["<b>CRISM pipeline</b>"]
    direction TB
        C_proc["<b>Pre-processing</b><br>projection, mosaics, 100x100 grid"]
        C_feat["<b>Feature extraction</b><br>%H₂O, %Fe/Mg, %Al-OH"]
        C_dec["<b>Decision criteria<br></b>quantile-based<br>high %H₂O or <br>medium %H₂O + %Fe/Mg"]
        C_out@{ label: "<b><span style=\"--tw-scale-x:\">Feature table</span><br style=\"--tw-scale-x:\"></b>per grid cell" }
  end
 subgraph THEMIS_PIPE["<b>THEMIS pipeline</b>"]
    direction TB
        T_proc["<b>Pre-processing</b><br>projection, BT mosaics per LST, 100×100 grid"]
        T_feat["<b>Feature extraction</b><br>per-slot median temperatures"]
        T_dec["<b>Decision criteria</b><br>rover -100°C&lt;T&lt;40°C<br>helicopter T&gt;-100°C"]
        T_out@{ label: "<span style=\"--tw-scale-x:\"><b>Feature table</b></span><br style=\"--tw-scale-x:\">per grid cell" }
  end
 subgraph FUSION["<b>Feature fusion &amp; ML</b>"]
    direction TB
        MERGE["<b>Merged dataset</b><br>MOLA + CRISM + THEMIS <br>per grid cell"]
        REG["<b>Linear regression model</b><br>training and validation on 80% dataset<br>testing on 20% dataset"]
  end
    M_proc --> M_feat
    M_feat --> M_dec
    M_dec --> M_out
    C_proc --> C_feat
    C_feat --> C_dec
    C_dec --> C_out
    T_proc --> T_feat
    T_feat --> T_dec
    T_dec --> T_out
    MERGE --> REG
    R_M --> MOLA_PIPE
    R_C --> CRISM_PIPE
    R_T --> THEMIS_PIPE
    MOLA_PIPE --> FUSION
    CRISM_PIPE --> FUSION
    REG --> n1["<b>Predicted landing suitability</b><br>per grid cell and time slot"]
    THEMIS_PIPE --> FUSION
    R_M@{ shape: cyl}
    R_C@{ shape: cyl}
    R_T@{ shape: cyl}
    C_out@{ shape: rect}
    T_out@{ shape: rect}
    MERGE@{ shape: stored-data}
    n1@{ shape: display}
    style R_M stroke:#D50000,stroke-width:4px,stroke-dasharray: 0
    style R_C stroke:#D50000,stroke-width:4px,stroke-dasharray: 0
    style R_T stroke:#D50000,stroke-width:4px,stroke-dasharray: 0
    style FUSION color:#000000
    style FUSION fill:#C8E6C9
    style n1 fill:#FFFFFF,stroke:#00C853,color:#000000,stroke-width:4px,stroke-dasharray: 0
    style RAW fill:#FFCDD2,color:#000000
