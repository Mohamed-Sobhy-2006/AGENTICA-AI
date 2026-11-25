import os
import shutil
import zipfile
from PIL import Image


def build_tests_data(
    invoices_pdf_zip: str = "invoices_pdfs_and_labels (1).zip",
    invoices_img_zip: str = "invoices_batch2_50 (1).zip",
    cvs_zip: str = "AGENTICA_FINAL_2050 (1) (3).zip",
    output_dir: str = "tests/data",
) -> None:
    """
    Assemble 20 OCR smoke-test files in tests/data/ for P4:
      - 5 native digital PDF invoices (from invoices_pdfs_and_labels)
      - 5 scanned/image-based PDF invoices (converted from JPG batch 2)
      - 10 PDF CVs across diverse layouts (ATS templates, dense, enhancv, undergrad, real Kaggle)
    """
    os.makedirs(output_dir, exist_ok=True)
    tmp_dir = "_tmp_ocr_extract"
    os.makedirs(tmp_dir, exist_ok=True)

    # 1. Extract 5 native digital PDF invoices
    with zipfile.ZipFile(invoices_pdf_zip, "r") as zf:
        pdf_invoices = sorted([f for f in zf.namelist() if f.endswith(".pdf")])[:5]
        for f in pdf_invoices:
            zf.extract(f, tmp_dir)
            shutil.copy(
                os.path.join(tmp_dir, f),
                os.path.join(output_dir, os.path.basename(f)),
            )

    # 2. Extract 5 JPG invoices and convert them to image-based (scanned) PDFs
    with zipfile.ZipFile(invoices_img_zip, "r") as zf:
        jpg_invoices = sorted([f for f in zf.namelist() if f.lower().endswith(".jpg")])[:5]
        for f in jpg_invoices:
            zf.extract(f, tmp_dir)
            img_path = os.path.join(tmp_dir, f)
            pdf_name = os.path.splitext(os.path.basename(f))[0] + "_scanned.pdf"
            with Image.open(img_path) as im:
                im.convert("RGB").save(os.path.join(output_dir, pdf_name), "PDF", resolution=150.0)

    # 3. Extract 10 diverse CV PDFs
    selected_cvs = [
        "cv_0007_template_1.pdf",
        "cv_0020_template_2.pdf",
        "cv_0045_template_3.pdf",
        "cv_0010_template_4.pdf",
        "dense_0002.pdf",
        "dense_0010.pdf",
        "enhancv_0002.pdf",
        "enhancv_0006.pdf",
        "undergrad_0003.pdf",
        "11850315.pdf",
    ]
    with zipfile.ZipFile(cvs_zip, "r") as zf:
        available = set(zf.namelist())
        picked = [c for c in selected_cvs if c in available]
        if len(picked) < 10:
            extra = [f for f in sorted(available) if f.endswith(".pdf") and f not in picked]
            picked.extend(extra[: 10 - len(picked)])
        for f in picked[:10]:
            zf.extract(f, tmp_dir)
            shutil.copy(
                os.path.join(tmp_dir, f),
                os.path.join(output_dir, f"cv_{os.path.basename(f)}"),
            )

    shutil.rmtree(tmp_dir, ignore_errors=True)
    files = sorted(os.listdir(output_dir))
    print(f"Prepared {len(files)} files in '{output_dir}':")
    for name in files:
        print(f"  - {name}")


if __name__ == "__main__":
    build_tests_data()