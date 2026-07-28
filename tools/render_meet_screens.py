import argparse
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import (  # noqa: E402
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QWidget,
)


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _validator_layout(label):
    layout = QHBoxLayout()
    layout.addWidget(QLabel(label))
    layout.addWidget(QLineEdit())
    return layout


def _load_view_modules():
    with patch("mongoengine.connect", return_value=None):
        from modelos.ParametrosSistema import ParamSist

    with patch.object(
        ParamSist,
        "ObtenerParametro",
        side_effect=lambda parametro, default=None: default,
    ):
        import vistas.ABMClientes as clientes_mod
        import vistas.ImportacionPedidos as importacion_mod
        import vistas.Login as login_mod
        import vistas.VerHojaRuta as ruta_mod

    return ParamSist, login_mod, clientes_mod, importacion_mod, ruta_mod


def render_screens(output_dir):
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    application = QApplication.instance() or QApplication([])
    original_argv = sys.argv[:]
    sys.argv = [
        "render_meet_screens",
        "-i",
        str(ROOT),
        "-a",
        "sistema.ini",
    ]

    try:
        (
            ParamSist,
            login_mod,
            clientes_mod,
            importacion_mod,
            ruta_mod,
        ) = _load_view_modules()
        from pyqt5libs.pyqt5libs import utiles as qt_utiles

        parameter_patch = patch.object(
            ParamSist,
            "ObtenerParametro",
            side_effect=lambda parametro, default=None: default,
        )
        network_patch = patch(
            "socket.socket.connect",
            side_effect=AssertionError("La validación visual no permite red"),
        )
        runtime_path_patch = patch.object(
            qt_utiles,
            "ubicacion_sistema",
            return_value=str(ROOT),
        )

        with parameter_patch, network_patch, runtime_path_patch:
            with patch.object(login_mod, "CboUsuario", QComboBox):
                login_view = login_mod.LoginView()

            with patch.object(
                clientes_mod.ABM,
                "ArmaDatos",
                return_value=None,
            ), patch.object(
                clientes_mod.ABM,
                "ArmaTabla",
                return_value=None,
            ):
                clientes_view = clientes_mod.ABMClientesView()

            with patch.object(
                importacion_mod,
                "ValidaProveedor",
                side_effect=lambda *args, **kwargs: _validator_layout(
                    "Empresa proveedora"
                ),
            ):
                importacion_view = importacion_mod.ImportacionPedidosView()

            with patch.object(ruta_mod, "cboRutaReparto", QComboBox), patch.object(
                ruta_mod,
                "ValidaEquipo",
                side_effect=lambda *args, **kwargs: _validator_layout(
                    "Camión asignado"
                ),
            ), patch.object(
                ruta_mod,
                "ValidaEmpleado",
                side_effect=lambda *args, **kwargs: _validator_layout(
                    "Chofer responsable"
                ),
            ):
                ruta_view = ruta_mod.VerHojaRutaView()

        views = {
            "login": login_view,
            "clientes": clientes_view,
            "importacion_pedidos": importacion_view,
            "hoja_ruta": ruta_view,
        }
        manifest = {}
        for name, view in views.items():
            image_path = output_path / "{}.png".format(name)
            view.show()
            application.processEvents()
            if not view.grab().save(str(image_path), "PNG"):
                raise RuntimeError(
                    "No se pudo guardar la captura {}".format(image_path)
                )
            pixmaps = [
                label.pixmap()
                for label in view.findChildren(QLabel)
                if label.pixmap() is not None and not label.pixmap().isNull()
            ]
            manifest[name] = {
                "path": str(image_path),
                "title": view.windowTitle(),
                "width": view.width(),
                "height": view.height(),
                "controls": len(view.findChildren(QWidget)),
                "images": len(pixmaps),
                "max_image_width": max(
                    (pixmap.width() for pixmap in pixmaps),
                    default=0,
                ),
            }
            view.close()
        application.processEvents()
        return manifest
    finally:
        sys.argv = original_argv


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Renderiza pantallas RND sin acceso a base ni red."
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "artifacts" / "meet-screens"),
        help="Directorio de salida de las capturas.",
    )
    arguments = parser.parse_args(argv)
    manifest = render_screens(arguments.output)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
