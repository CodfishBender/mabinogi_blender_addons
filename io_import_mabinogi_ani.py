bl_info= {
    "name": "Import Mabinogi Pleione Animation",
    "author": "Tachiorz",
    "version": (0, 2),
    "blender": (2, 80, 0),
    "location": "File > Import > Mabinogi Animation (.ani)",
    "description": "Imports a Mabinogi Animation file",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import"
}

import os, struct

import bpy
import mathutils

class MabinogiFrame():
    mTime = 0
    move = (0.0, ) * 4
    roto = (0.0, ) * 4

class MabinogiAniData():
    mDataCount = 0
    mTime = 0
    mSize = 0
    frames = list() # of MabinogiFrame()

class MabinogiAnimation:
    frameCount = 0
    baseTime = 0
    boneCount = 0
    bone = list() # of MabinogiData()
    unknown_ani = list()

    def __init__(self):
        self.bone = list()
        self.unknown_ani = list()

def load_ani(filename, context):
    name, ext= os.path.splitext(os.path.basename(filename))
    file= open(filename, 'rb')
    ani = MabinogiAnimation()
    try:
        magic, version, ani.frameCount, _, ani.baseTime, _, ani.boneCount  = struct.unpack("<4sihhhii", file.read(22))
    except:
        print("Error parsing file header!")
        file.close()
        return
    if magic != b'pa!\x00':
        print("Not a supported file type!")
        file.close()
        return
    file.seek(9*4, os.SEEK_CUR)
    for b in range(ani.boneCount):
        ani.bone += [MabinogiAniData(),]
        _, ani.bone[b].mDataCount, _, ani.bone[b].mTime, ani.bone[b].mSize = struct.unpack("<ihhii", file.read(16))
        file.seek(2*4, os.SEEK_CUR)
        ani.bone[b].frames = list()
        print ("bone %d" % b)
        for f in range(ani.bone[b].mDataCount):
            ani.bone[b].frames += [MabinogiFrame(),]
            ani.bone[b].frames[f].mTime = struct.unpack("<i", file.read(4))[0]
            ani.bone[b].frames[f].move = struct.unpack("<4f", file.read(16))
            ani.bone[b].frames[f].roto = list(struct.unpack("<4f", file.read(16)))
            ani.bone[b].frames[f].roto = [-ani.bone[b].frames[f].roto[3]] + ani.bone[b].frames[f].roto[:3]
            if f == 0:
                print (ani.bone[b].frames[f].mTime)
                print ("%.2f %.2f %.2f %.2f" % ani.bone[b].frames[f].move)
                print ("%.2f %.2f %.2f %.2f" % tuple(ani.bone[b].frames[f].roto))


    #find if the selected object is a an armature
    armature = None
    sel_ob = context.active_object
    if sel_ob is not None and sel_ob.type == 'ARMATURE':
        armature = sel_ob.data
    else:
        print("No armature selected")
        return
    if len(armature.bones) != ani.boneCount:
        print("Bone count doesn't match")
    sel_ob.animation_data_create()
    action = bpy.data.actions.new(name=name)
    sel_ob.animation_data.action = action
    pb = sel_ob.pose.bones
    eb = sel_ob.data.bones
    pose_bones = dict()
    edit_bones = dict()
    for i in range(len(pb)):
        bone_id = int(pb[i].name[:pb[i].name.index('__')])
        pose_bones[bone_id] = pb[i]
        edit_bones[bone_id] = pb[i].bone
    bone_space = mathutils.Matrix(((0, 1, 0, 0),
                                   (0, 0, 1, 0),
                                   (1, 0, 0, 0),
                                   (0, 0, 0, 1)))
    for b in range(ani.boneCount):
        prev_quat = None
        for f in range(ani.bone[b].mDataCount):
            frame = ani.bone[b].frames[f].mTime/50
            pos = ani.bone[b].frames[f].move[:3]
            quat = mathutils.Quaternion(ani.bone[b].frames[f].roto)
            mat = mathutils.Matrix.Translation(pos) @ quat.to_matrix().to_4x4()
            link = edit_bones[b].matrix_local @ bone_space.inverted()
            if edit_bones[b].parent is not None:
                parent_link = edit_bones[b].parent.matrix_local @ bone_space.inverted()
                link = parent_link.inverted() @ link
            mat = mat @ bone_space
            link = link @ bone_space
            pose_bones[b].matrix_basis = link.inverted() @ mat
            # keep quaternion sign consistent between keys, otherwise
            # interpolation passes through a degenerate rotation
            if prev_quat is not None:
                q = pose_bones[b].rotation_quaternion.copy()
                q.make_compatible(prev_quat)
                pose_bones[b].rotation_quaternion = q
            prev_quat = pose_bones[b].rotation_quaternion.copy()
            pose_bones[b].keyframe_insert("rotation_quaternion", frame=frame)
            pose_bones[b].keyframe_insert("location", frame=frame)
            #bpy.context.scene.update()


from bpy.props import StringProperty

class IMPORT_MABINOGI_ani(bpy.types.Operator):
    '''Import ANI Operator.'''
    bl_idname= "import.ani"
    bl_label= "Import ANI"
    bl_description= "Import a Mabinogi Animation file"
    bl_options= {'REGISTER', 'UNDO'}

    filepath: StringProperty(name="File Path", description="Filepath used for importing the ANI file", maxlen=1024, default="", subtype='FILE_PATH')

    filter_glob: StringProperty(
        default = "*.ani",
        options = {'HIDDEN'},
    )

    def execute(self, context):
        load_ani(self.filepath,
            context)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm= context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

def menu_func_mabinogi_ani(self, context):
    self.layout.operator(IMPORT_MABINOGI_ani.bl_idname, text="Mabinogi Animation (.ani)")

class VIEW3D_PT_mabinogi_import_ani(bpy.types.Panel):
    '''Import button in the 3D viewport sidebar's Mabinogi tab.'''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mabinogi"
    bl_label = "Import Animation (.ani)"
    # no header, so the buttons from each Mabinogi addon stack into one list
    bl_options = {'HIDE_HEADER'}
    bl_order = 2

    def draw(self, context):
        self.layout.operator(IMPORT_MABINOGI_ani.bl_idname, text="Import Animation (.ani)", icon='ACTION')

def register():
    from bpy.utils import register_class
    register_class(IMPORT_MABINOGI_ani)
    register_class(VIEW3D_PT_mabinogi_import_ani)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_mabinogi_ani)


def unregister():
    from bpy.utils import unregister_class
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_mabinogi_ani)
    unregister_class(VIEW3D_PT_mabinogi_import_ani)
    unregister_class(IMPORT_MABINOGI_ani)

if __name__ == "__main__":
    register()
