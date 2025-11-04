# -*- coding: utf-8 -*-
import io, base64
import streamlit as st
import streamlit.components.v1 as components

# Tiny embedded PDF for demo purposes
DUMMY_PDF_BYTES = base64.b64decode(
    b'JVBERi0xLjAKMSAwIG9iajw8L1R5cGUvQ2F0YWxvZy9QYWdlcyAyIDAgUj4+ZW5kb2JqCjIgMCBvYmo8PC9UeXBlL1BhZ2VzL0NvdW50IDEvS2lkc1szIDAgUl0+PmVuZG9iagozIDAgb2JqPDwvVHlwZS9QYWdlL01lZGlhQm94WzAgMCAzMCAzMF0vUGFyZW50IDIgMCBSPj5lbmRvYmoKeHJlZgowIDQKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTIgMDAwMDAgbiAKMDAwMDAwMDA5OSAwMDAwMCBuIAp0cmFpbGVyPDwvU2l6ZSA0L1Jvb3QgMSAwIFI+PgpzdGFydHhyZWYKMTQ3CiUlRU9G'
)

def pdf_viewer_embed(file_bytes: bytes, filename: str, container=st, height=520):
    # 1) Native Streamlit
    try:
        container.pdf(file_bytes)
        return
    except Exception:
        pass

    # 2) Base64 <object> + <iframe> fallback
    try:
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        html = r"""
<div style="height:{H}px;border:1px solid #E3EDF6;border-radius:8px;overflow:hidden;background:#fff">
  <object data="data:application/pdf;base64,{B}#zoom=page-width"
          type="application/pdf" width="100%" height="{H}">
    <iframe src="data:application/pdf;base64,{B}#zoom=page-width"
            width="100%" height="{H}" style="border:0;">
    </iframe>
  </object>
</div>
""".format(H=height, B=b64)
        components.html(html, height=height+12, scrolling=False)
        try:
            container.markdown("[Abrir en pestaña nueva](data:application/pdf;base64:{})".format(b64))
        except Exception:
            pass
        return
    except Exception:
        pass

    # 3) Fallback: download
    try:
        container.download_button(
            label="⬇ Descargar PDF",
            data=file_bytes,
            file_name=filename if filename else "documento.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
        container.info("No fue posible mostrar el visor embebido. Descarga el PDF para verlo.")
    except Exception as e:
        container.error("No se pudo preparar el PDF: {}".format(e))

def main():
    st.set_page_config(page_title="SelektIA · Visor PDF Inline", page_icon="🧠", layout="wide")
    st.title("Demo Visor de PDF Inline (Base64)")
    st.write("Debajo debería verse un PDF embebido sin descarga forzada.")
    pdf_viewer_embed(DUMMY_PDF_BYTES, "demo.pdf", st, 520)

if __name__ == "__main__":
    main()
