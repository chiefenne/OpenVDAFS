# Minimal shaded 3D viewer using PySide6 Qt3D
# Deps: PySide6 only. Works with your reader/index/curve_eval/surf_eval modules.
#
# Usage:
#   python viewer_qt3d.py your.vda
#
# Notes:
# - Expects surf_eval.decode_surface_entity(entity) -> surface_obj
#           and surf_eval.sample_surface(surface_obj, nu, nv) -> (vertices Nx3, faces Mx3)
# - Expects curve_eval.decode_curve_entity(entity) and curve_eval.sample_curve(curve, spp)

import sys, numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.Qt3DExtras import Qt3DWindow, QOrbitCameraController, QPhongMaterial
from PySide6.Qt3DCore import QEntity, QTransform
from PySide6.Qt3DRender import (QGeometry, QAttribute, QBuffer, QGeometryRenderer,
                                QCamera, QPointLight)
from PySide6.QtGui import QVector3D

import reader, index, curve_eval as ce, surf_eval as se  # your modules

def _np_to_bytes(arr, dtype=np.float32):
    a = np.asarray(arr, dtype=dtype)
    return a.tobytes(), a

def _compute_vertex_normals(verts, faces):
    V = np.asarray(verts, dtype=np.float32)
    F = np.asarray(faces, dtype=np.int32)
    N = np.zeros_like(V, dtype=np.float32)
    v0 = V[F[:,0]]; v1 = V[F[:,1]]; v2 = V[F[:,2]]
    fn = np.cross(v1 - v0, v2 - v0)
    # accumulate face normals to vertices
    for i in range(3):
        np.add.at(N, F[:, i], fn)
    # normalize
    lens = np.linalg.norm(N, axis=1)
    lens[lens == 0] = 1.0
    N /= lens[:, None]
    return N

def make_mesh_entity(root, vertices, faces, color=(0.78, 0.82, 0.9)):
    verts = np.asarray(vertices, dtype=np.float32)
    faces = np.asarray(faces, dtype=np.uint32)
    norms = _compute_vertex_normals(verts, faces)

    geom = QGeometry(root)

    # --- Vertex buffer (positions) ---
    vbuf = QBuffer(geom)
    vbytes, _ = _np_to_bytes(verts, np.float32)
    vbuf.setData(vbytes)

    pos_attr = QAttribute(geom)
    pos_attr.setName(QAttribute.defaultPositionAttributeName())
    pos_attr.setBuffer(vbuf)
    pos_attr.setVertexBaseType(QAttribute.Float)
    pos_attr.setVertexSize(3)
    pos_attr.setByteOffset(0)
    pos_attr.setByteStride(12)  # 3 * 4 bytes
    pos_attr.setCount(verts.shape[0])

    # --- Normal buffer ---
    nbuf = QBuffer(geom)
    nbytes, _ = _np_to_bytes(norms, np.float32)
    nbuf.setData(nbytes)

    n_attr = QAttribute(geom)
    n_attr.setName(QAttribute.defaultNormalAttributeName())
    n_attr.setBuffer(nbuf)
    n_attr.setVertexBaseType(QAttribute.Float)
    n_attr.setVertexSize(3)
    n_attr.setByteOffset(0)
    n_attr.setByteStride(12)
    n_attr.setCount(norms.shape[0])

    # --- Index buffer ---
    ibuf = QBuffer(geom)
    ibytes, _ = _np_to_bytes(faces.ravel(), np.uint32)
    ibuf.setData(ibytes)

    idx_attr = QAttribute(geom)
    idx_attr.setAttributeType(QAttribute.IndexAttribute)
    idx_attr.setBuffer(ibuf)
    idx_attr.setVertexBaseType(QAttribute.UnsignedInt)
    idx_attr.setCount(faces.size)

    geom.addAttribute(pos_attr)
    geom.addAttribute(n_attr)
    geom.addAttribute(idx_attr)

    mesh = QGeometryRenderer(root)
    mesh.setGeometry(geom)
    mesh.setPrimitiveType(QGeometryRenderer.Triangles)

    mat = QPhongMaterial(root)
    mat.setAmbient(Qt3DWindow().defaultFrameGraph().clearColor())  # mild ambient
    # tweak diffuse/specular a bit via setDiffuse/setSpecular if you like

    ent = QEntity(root)
    ent.addComponent(mesh)
    ent.addComponent(mat)
    return ent

def make_line_entity(root, points):
    pts = np.asarray(points, dtype=np.float32)
    geom = QGeometry(root)

    # vertex buffer
    vbuf = QBuffer(geom)
    vbytes, _ = _np_to_bytes(pts, np.float32)
    vbuf.setData(vbytes)

    pos_attr = QAttribute(geom)
    pos_attr.setName(QAttribute.defaultPositionAttributeName())
    pos_attr.setBuffer(vbuf)
    pos_attr.setVertexBaseType(QAttribute.Float)
    pos_attr.setVertexSize(3)
    pos_attr.setByteOffset(0)
    pos_attr.setByteStride(12)
    pos_attr.setCount(pts.shape[0])

    geom.addAttribute(pos_attr)

    r = QGeometryRenderer(root)
    r.setGeometry(geom)
    r.setPrimitiveType(QGeometryRenderer.LineStrip)

    mat = QPhongMaterial(root)  # simple material (color will default)
    ent = QEntity(root)
    ent.addComponent(r)
    ent.addComponent(mat)
    return ent

def load_scene(root, path, surf_samples=(80,80), curve_spp=60):
    m = reader.read_vdafs(path)
    idx = index.build_index(m)

    # SURF meshes
    for name in idx['by_type'].get('SURF', []):
        ent = idx['by_name'][name]
        s = se.decode_surface_entity(ent)               # your API
        xyz, faces = se.sample_surface(s, *surf_samples)  # (N,3), (M,3)
        make_mesh_entity(root, xyz, faces)

    # CURVE polylines
    for name in idx['by_type'].get('CURVE', []):
        e = idx['by_name'][name]
        c = ce.decode_curve_entity(e)
        pts = ce.sample_curve(c, samples_per_segment=curve_spp)
        make_line_entity(root, pts)

def main(vda_path):
    app = QApplication(sys.argv)

    view = Qt3DWindow()
    view.defaultFrameGraph().setClearColor("#1e1e1e")
    container = view

    root = QEntity()

    # Camera
    cam = view.camera()
    cam.setPosition(QVector3D(250.0, 200.0, 250.0))
    cam.setViewCenter(QVector3D(0.0, 0.0, 0.0))
    cam.setUpVector(QVector3D(0.0, 0.0, 1.0))

    # Light
    lightEnt = QEntity(root)
    light = QPointLight(lightEnt)
    light.setIntensity(1.0)
    lightEnt.addComponent(light)
    ltXform = QTransform()
    ltXform.setTranslation(QVector3D(300, 300, 300))
    lightEnt.addComponent(ltXform)

    # Orbit controller
    ctrl = QOrbitCameraController(root)
    ctrl.setCamera(cam)
    ctrl.setLinearSpeed(200)
    ctrl.setLookSpeed(180)

    # Load geometry
    load_scene(root, vda_path)

    view.setRootEntity(root)
    view.resize(1200, 800)
    view.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python viewer_qt3d.py file.vda")
        sys.exit(1)
    main(sys.argv[1])
