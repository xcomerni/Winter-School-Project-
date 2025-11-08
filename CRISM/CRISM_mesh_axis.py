# Create a new plot based on the first plot's setup, but with mesh cell indices on axes

if 'img' in locals() and 'extent' in locals() and \
   'crop_xmin' in locals() and 'crop_xmax' in locals() and \
   'crop_ymin' in locals() and 'crop_ymax' in locals():

    plt.figure(figsize=(10, 10))
    ax_combined = plt.gca()

    # Set the background color inside the plot to white
    ax_combined.set_facecolor('white')

    # Display the image using the original extent
    im_combined = ax_combined.imshow(img, extent=extent, origin='upper', interpolation='nearest')

    plt.title("Jezero CRISM SR RGB Mesh")

    # Apply the same cropping as the first plot using EQC limits
    ax_combined.set_xlim(crop_xmin, crop_xmax)
    ax_combined.set_ylim(crop_ymin, crop_ymax)

    # Ensure the aspect ratio is equal to prevent stretching
    ax_combined.set_aspect('equal', adjustable='box')

    # --- Add the 100x100 mesh lines ---
    # Get the current plot limits (which are the cropped EQC limits)
    current_xlim = ax_combined.get_xlim()
    current_ylim = ax_combined.get_ylim()

    # Calculate the step size for the mesh lines based on the cropped EQC extent
    x_step_mesh_lines = (current_xlim[1] - current_xlim[0]) / 100
    y_step_mesh_lines = (current_ylim[1] - current_ylim[0]) / 100

    # Create the mesh lines
    x_lines_mesh = np.linspace(current_xlim[0], current_xlim[1], 101) # 100 divisions means 101 lines
    y_lines_mesh = np.linspace(current_ylim[0], current_ylim[1], 101) # 100 divisions means 101 lines

    # Add vertical lines
    for x in x_lines_mesh:
        ax_combined.axvline(x, color='black', linestyle='-', linewidth=0.5)

    # Add horizontal lines
    for y in y_lines_mesh:
        ax_combined.axhline(y, color='black', linestyle='-', linewidth=0.5)
    # --- End mesh lines ---


    # --- Set axis labels to mesh cell indices ---
    # Need to map the EQC coordinates of the cropped extent to the pixel index space [0-100]
    # Get the original image extent in EQC from the first plotting cell (XPyMDBaH6NKo)
    # Assuming 'extent' is available from XPyMDBaH6NKo
    original_eqc_xmin, original_eqc_xmax, original_eqc_ymin, original_eqc_ymax = extent

    # Calculate the scaling factors from EQC to pixel index space [0-100]
    scale_x = 100.0 / (original_eqc_xmax - original_eqc_xmin)
    scale_y = 100.0 / (original_eqc_ymax - original_eqc_ymin) # Note: y-axis is inverted in pixel space

    # Define tick locations in EQC coordinates based on the cropped extent
    # We want ticks that correspond to the mesh cell boundaries in the cropped area
    # Calculate the EQC coordinates of the mesh cell boundaries within the cropped area
    cropped_pixel_xmin = (crop_xmin - original_eqc_xmin) * scale_x
    cropped_pixel_ymin = (original_eqc_ymax - crop_ymax) * scale_y # Map original_eqc_ymax to pixel 0
    cropped_pixel_xmax = (crop_xmax - original_eqc_xmin) * scale_x
    cropped_pixel_ymax = (original_eqc_ymax - crop_ymin) * scale_y # Map original_eqc_ymin to pixel 100


    # Define tick locations in terms of mesh cell indices (e.g., every 10 cells)
    mesh_index_ticks = np.arange(0, 101, 10)

    # Transform these mesh index ticks back to the EQC coordinates within the cropped extent
    # Need to scale the mesh index ticks to the range of the cropped EQC limits
    cropped_eqc_xticks = crop_xmin + (mesh_index_ticks / 100.0) * (crop_xmax - crop_xmin)
    # Need to handle the y-axis inversion for the EQC transformation
    # pixel 0 (top) corresponds to ymax_eqc, pixel 100 (bottom) corresponds to ymin_eqc
    # The mesh index 0 corresponds to the top of the cropped area (ymax_eqc)
    # The mesh index 100 corresponds to the bottom of the cropped area (ymin_eqc)
    # A mesh index 'i' corresponds to a position that is 'i/100' of the way down from the top of the cropped area
    # The EQC y-coordinate for a mesh index 'i' is ymax_cropped_eqc - (i/100.0) * (ymax_cropped_eqc - ymin_cropped_eqc)
    cropped_eqc_yticks = crop_ymax - (mesh_index_ticks / 100.0) * (crop_ymax - crop_ymin)


    # Set the tick positions using the calculated EQC coordinates within the cropped extent
    ax_combined.set_xticks(cropped_eqc_xticks)
    ax_combined.set_yticks(cropped_eqc_yticks)

    # Set the tick labels to the mesh cell indices
    ax_combined.set_xticklabels([str(int(i)) for i in mesh_index_ticks])
    ax_combined.set_yticklabels([str(int(i)) for i in mesh_index_ticks]) # Labels are the same for x and y indices

    ax_combined.set_xlabel("Mesh Cell X Index")
    ax_combined.set_ylabel("Mesh Cell Y Index")
    # --- End set axis labels ---


    # Optionally, add the legend text again
    legend_text = """
R = D2300 (Fe/Mg)
G = BD2210 (Al-OH)
B = BD1900 (H2O)
    """
    plt.text(
        1.02, # X-coordinate relative to the axes (1.0 is the right edge)
        1.0,  # Y-coordinate relative to the axes (1.0 is the top edge)
        legend_text.strip(),
        color='black',
        fontsize=10,
        ha='left',
        va='top',
        transform=ax_combined.transAxes,
        bbox=dict(facecolor='white', alpha=0.8, edgecolor='black')
    )

    plt.tight_layout(rect=[0, 0, 0.8, 1]) # Adjust rect to make space for the legend
    plt.show()

else:
    print("Errore: Variabili necessarie (img, extent, crop_xmin, etc.) non trovate. Assicurati di aver eseguito le celle precedenti.")
