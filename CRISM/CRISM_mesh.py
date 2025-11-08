# Add a 100x100 mesh to the current plot

# Receive fig and ax from the previous cell
if 'fig' in locals() and 'ax' in locals():
    # Get the current axes object from the previous plot
    current_xlim = ax.get_xlim()
    current_ylim = ax.get_ylim()

    # Calculate the step size for the mesh lines
    x_step = (current_xlim[1] - current_xlim[0]) / 100
    y_step = (current_ylim[1] - current_ylim[0]) / 100

    # Create the mesh lines
    x_lines = np.linspace(current_xlim[0], current_xlim[1], 101) # 100 divisions means 101 lines
    y_lines = np.linspace(current_ylim[0], current_ylim[1], 101) # 100 divisions means 101 lines

    # Add vertical lines
    for x in x_lines:
        ax.axvline(x, color='black', linestyle='-', linewidth=0.5)

    # Add horizontal lines
    for y in y_lines:
        ax.axhline(y, color='black', linestyle='-', linewidth=0.5)

    # Redraw the canvas to show the mesh
    plt.draw()

    # --- Save and display the figure ---
    # Define a path to save the figure
    meshed_image_path = os.path.join(OUT_DIR, "jezero_CRISM_RGB_mosaic_meshed.png")

    # Save the figure
    fig.savefig(meshed_image_path, bbox_inches='tight', pad_inches=0.1)
    print(f"Grafico con mesh salvato come: {meshed_image_path}")

    # Close the figure to prevent it from being displayed again by plt.show()
    plt.close(fig)

    # Display the saved image file
    try:
        from IPython.display import Image, display
        display(Image(filename=meshed_image_path))
        print("Grafico con mesh visualizzato come immagine.")
    except Exception as e:
        print(f"Errore durante la visualizzazione dell'immagine salvata: {e}")
    # --- End Save and display the figure ---

    # plt.show() # Remove this as we are displaying the saved image
    print("Mesh 100x100 aggiunta al grafico.")
else:
    print("Errore: Impossibile trovare gli oggetti 'fig' o 'ax'. Assicurati di aver eseguito correttamente la cella precedente per generare il grafico.")
