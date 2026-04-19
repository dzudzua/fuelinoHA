class FuelioUploadPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
  }

  set panel(panel) {
    this._panel = panel;
    this.render();
  }

  connectedCallback() {
    this.render();
  }

  render() {
    const uploadFolder = this._panel?.config?.upload_folder ?? "";
    this.innerHTML = `
      <style>
        :host {
          display: block;
          padding: 24px;
          color: var(--primary-text-color);
        }
        .wrap {
          max-width: 720px;
          margin: 0 auto;
        }
        ha-card {
          display: block;
          padding: 24px;
        }
        .hint {
          color: var(--secondary-text-color);
          margin: 8px 0 20px;
          line-height: 1.5;
        }
        .path {
          font-family: monospace;
          background: var(--secondary-background-color);
          padding: 10px 12px;
          border-radius: 8px;
          word-break: break-all;
          margin-bottom: 20px;
        }
        .row {
          display: flex;
          gap: 12px;
          align-items: center;
          flex-wrap: wrap;
        }
        .status {
          margin-top: 18px;
          padding: 12px;
          border-radius: 8px;
          background: var(--secondary-background-color);
          white-space: pre-wrap;
        }
      </style>
      <div class="wrap">
        <ha-card header="Fuelio CSV Upload">
          <p class="hint">
            Nahraj CSV export z Fuelio primo z pocitace nebo telefonu.
            Soubor se ulozi do slozky, kterou Home Assistant vidi lokalne.
          </p>
          <div class="path">${uploadFolder}</div>
          <div class="row">
            <input id="file" type="file" accept=".csv,text/csv" />
            <mwc-button id="upload" raised>Upload CSV</mwc-button>
          </div>
          <div id="status" class="status">Pripraveno k uploadu.</div>
        </ha-card>
      </div>
    `;

    this.querySelector("#upload")?.addEventListener("click", async () => {
      const fileInput = this.querySelector("#file");
      const status = this.querySelector("#status");
      const file = fileInput?.files?.[0];
      if (!file) {
        status.textContent = "Vyber CSV soubor.";
        return;
      }

      const formData = new FormData();
      formData.append("file", file, file.name);

      status.textContent = "Nahravam...";

      try {
        const response = await fetch("/api/fuelio/upload", {
          method: "POST",
          body: formData,
        });
        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.error || "upload_failed");
        }
        status.textContent =
          "Hotovo.\nUlozeno do: " +
          result.saved_path +
          "\nPokud mas Fuelio nastaveny na tuto slozku nebo soubor, data se obnovi automaticky.";
      } catch (err) {
        status.textContent = "Upload selhal: " + err.message;
      }
    });
  }
}

customElements.define("fuelio-upload-panel", FuelioUploadPanel);
