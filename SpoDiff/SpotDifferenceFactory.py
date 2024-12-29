import traceback
import adsk.core as core
import adsk.fusion as fusion
import bisect as bs


class SpotDifferenceFactory():
    def __init__(
            self, 
            bodyA: fusion.BRepBody, 
            bodyB: fusion.BRepBody):

        self.app: core.Application = core.Application.get()
        self.ui: core.UserInterface = self.app.userInterface

        self.bodyA: fusion.BRepBody = bodyA
        self.bodyB: fusion.BRepBody = bodyB

        self.diffFaces1: list[fusion.BRepFace] = None
        self.diffFaces2: list[fusion.BRepFace] = None

        # #拡張
        # fusion.Component.toOcc = to_occurrenc
        # fusion.Component.activate = comp_activate

    def get_bodies_info(self) -> str:

        msg = "Bodyが２個設定されていません"
        if not self.bodyA:
            self.ui.messageBox(msg)
            return ""

        if not self.bodyB:
            self.ui.messageBox(msg)
            return ""

        msg = "２個のボディが同じです"
        if self.bodyA == self.bodyB:
            self.ui.messageBox(msg)
            return ""

        # コンポーネントの位置
        mat1a, mat2a, mat2_1 = get_matrix(
            self.bodyA,
            self.bodyB,
        )

        # 異なる面取得
        self.diffFaces1, self.diffFaces2 = get_unmatched_faces(
            self.bodyA,
            self.bodyB,
            mat2_1,
            0.001
        )

        hit1 = len(self.diffFaces1)
        hit2 = len(self.diffFaces2)
        if hit1 < 1 and hit2 < 1:
            return "異なる部分を見つけることが出来ませんでした"

        faceCount1 = self.bodyA.faces.count
        faceCount2 = self.bodyB.faces.count
        msg ="\n".join(
            [
                f"{self.bodyA.name} - 異なる面数/全体数 : {hit1}/{faceCount1}",
                f"{self.bodyB.name} - 異なる面数/全体数 : {hit2}/{faceCount2}",
            ]
        )

        #安全策 10%
        #あまり異なると処理に時間がかかる上、比較自体に意味が無い
        if (hit1*100//faceCount1) > 10 or (hit2*100//faceCount2) > 10:
            return msg + "\n異なる部分が多数有ります。"
        else:
            return msg


    def create_diff_faces(self):
        """
        差分面作成
        """
        create_clone_face(self.diffFaces1, self.bodyA)
        create_clone_face(self.diffFaces2, self.bodyB)


def create_clone_face(
        faces: list[fusion.BRepFace],
        body: fusion.BRepBody,):

    if len(faces) < 1: return

    occ: fusion.Occurrence = body.assemblyContext
    if occ:
        mat: core.Matrix3D = occ.transform2
        mat.invert()
    else:
        mat: core.Matrix3D = core.Matrix3D.create()

    tmpMgr: fusion.TemporaryBRepManager = fusion.TemporaryBRepManager.get()

    baseBody: fusion.BRepBody = tmpMgr.copy(faces[0])
    tmpMgr.transform(baseBody, mat)

    if len(faces) > 2:
        for f in faces[1:]:
            try:
                f = tmpMgr.copy(f)
                tmpMgr.transform(f, mat)
                res = tmpMgr.booleanOperation(
                    baseBody,
                    f,
                    fusion.BooleanTypes.UnionBooleanType,
                )
            except:
                print("Union Err")

    comp: fusion.Component = body.parentComponent
    des: fusion.Design = comp.parentDesign

    baseFeat: fusion.BaseFeature = None
    if des.designType == fusion.DesignTypes.ParametricDesignType:
        baseFeat = comp.features.baseFeatures.add()

    bodies: fusion.BRepBodies = comp.bRepBodies
    resBody: fusion.BRepBody = None
    if baseFeat:
        try:
            baseFeat.startEdit()
            resBody = bodies.add(baseBody, baseFeat)
        except:
            pass
        finally:
            baseFeat.finishEdit()
            baseFeat.bodies[0].name = f"{body.name}_UnmatchedFace"
    else:
        resBody = bodies.add(baseBody)
        resBody.name = f"{body.name}_UnmatchedFace"


def refresh_display():
    """
    画面のリフレッシュ
    """
    app: core.Application = core.Application.get()
    ui: core.UserInterface = app.userInterface
    ui.activeSelections.clear()
    app.activeViewport.refresh_display()


def get_unmatched_faces(
        body1,
        body2,
        mat,
        tolerance=0.001) -> tuple:
    """
    異なる面の検索
    """

    if body1 is None or body2 is None:
        return
    
    fusion.BRepFace.isOverRap = False
    fusion.BRepFace.transform_centroid = None
    
    faces1 = sorted(body1.faces, key=lambda v: v.area)
    faces2 = sorted(body2.faces, key=lambda v: v.area)
    areas2 = [face.area for face in faces2]
    
    for face in faces2:
        face.transform_centroid = transform_clone(
            face.centroid,
            mat
        ) 
    
    for f1 in faces1:
        if f1.isOverRap:
            continue
        
        f1cog: core.Point3D = f1.centroid
        lwr = bs.bisect_left(areas2,f1.area - tolerance)
        upr = bs.bisect_right(areas2,f1.area + tolerance)
        
        for f2 in faces2[lwr:upr]:
            if f2.isOverRap == True:
                continue
            
            if f1cog.isEqualToByTolerance(f2.transform_centroid, tolerance):
                f1.isOverRap = True
                f2.isOverRap = True
    
    fs1 = [f for f in faces1 if f.isOverRap == False]
    fs2 = [f for f in faces2 if f.isOverRap == False]
    
    return fs1, fs2


def transform_clone(
        pnt: core.Point3D,
        mat: core.Matrix3D) -> core.Point3D:
    """
    Point3D 変換後のクローン作成
    """
    p: core.Point3D = pnt.copy()
    p.transformBy(mat)

    return p


def get_matrix(
        body1: fusion.BRepBody,
        body2: fusion.BRepBody) -> tuple:
    """
    オカレンス位置
    """
    occ1: fusion.Occurrence = body1.assemblyContext
    mat1: core.Matrix3D = core.Matrix3D.create()
    if not occ1 is None:
        mat1 = occ1.transform2
        
    occ2: fusion.Occurrence = body2.assemblyContext
    mat2: core.Matrix3D = core.Matrix3D.create()
    if not occ2 is None:
        mat2 = occ2.transform2
    
    #occ2→occ1へのマトリックス
    mat2_1: core.Matrix3D = mat2.copy()
    mat2_1.invert()
    mat2_1.transformBy(mat1)

    # dump_mat(mat1)
    # print("***")
    # dump_mat(mat1)
    # print("***")
    # dump_mat(mat2_1)

    return mat1, mat2, mat2_1


def dump_mat(mat: core.Matrix3D):

    p, vecX, vecY, vecZ = mat.getAsCoordinateSystem()
    print(p.asArray())
    print(vecX.asArray())
    print(vecY.asArray())
    print(vecZ.asArray())


# #-- 拡張メソッド --
# def comp_activate(self: fusion.Component):
#     """
#     adsk.fusion.Component 拡張メソッド
#     コンポーネントのアクティブ化
#     """
#     des: fusion.Design = self.parentDesign
#     occ: fusion.Occurrence = self.toOcc()
#     if occ is None:
#         des.activateRootComponent()
#     else:
#         occ.activate()


# def to_occurrenc(self: fusion.Component):
#     """
#     adsk.fusion.Component 拡張メソッド
#     コンポーネントからオカレンスの取得　ルートはNone
#     """
#     root: fusion.Component = self.parentDesign.rootComponent
#     if self == root:
#         return None
        
#     occs = [occ
#             for occ in root.allOccurrencesByComponent(self)
#             if occ.component == self]
#     return occs[0]