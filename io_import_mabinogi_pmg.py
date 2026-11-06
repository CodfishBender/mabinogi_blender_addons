bl_info= {
    "name": "Import Mabinogi Pleione Mesh Group",
    "author": "Tachiorz",
    "version": (0, 2),
    "blender": (2, 80, 0),
    "location": "File > Import > Mabinogi Mesh Group (.pmg)",
    "description": "Imports a Mabinogi Mesh Group file",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import"
}

import os
import re
import struct
import math

import bpy
import mathutils
from bpy_extras.image_utils import load_image

material_dict = None

class Vertex:
    x,y,z = 0,0,0
    nx,ny,nz = 0,0,0 # normals
    rgba = 0
    u,v = 0,0

class Skin:
    n = 0
    a = 0
    weight = 1.0
    b = 1
    
class MabinogiMesh:
    bone_name = ""
    mesh_name = ""
    texture_name = ""
    MinorMatrix = [[]*4 for i in range(4)]
    MajorMatrix = [[]*4 for i in range(4)]
    partNo = 0
    isAnimated = 0
    faceVertexCount = 0
    faceCount = 0
    stripFaceVertexCount = 0
    stripFaceCount = 0
    vertCount = 0
    skinCount = 0
    physicsCount = 0
    vertexList = list()
    stripVertexList = list()
    vertexArray = list()
    skinArray = list()
    physicsArray = list()
    morphFrameSize = 0
    morphFrames = ""  # placeholder, not used

def load_matrix4x4(file):
    m = mathutils.Matrix()
    for n in range(4):
        m[n][0:4] = struct.unpack("<4f", file.read(16))
    return m

def save_matrix4x4(file, m):
    for n in range(4):
        [file.write(struct.pack("<f", m[n][i])) for i in range(4)]
    return m
    
def load_quaternion(file):
    q = mathutils.Quaternion()
    q[0:5] = list(struct.unpack("<4f", file.read(16)))
    return q

def save_quaternion(file,q ):
    [file.write(struct.pack("<f", q[i])) for i in range(4)]
    return q

def load_lpstring(file):
    l = struct.unpack("<i", file.read(4))[0]
    return struct.unpack("<%ds" % l, file.read(l))[0].strip(b'\0').decode('utf-8', errors='replace')

def load_vertex(file):
    new_v = Vertex()
    new_v.x, new_v.y, new_v.z = struct.unpack("<fff", file.read(12))
    new_v.nx, new_v.ny, new_v.nz, new_v.rgba = struct.unpack("<fffi", file.read(16))
    new_v.u, new_v.v = struct.unpack("<ff", file.read(8))
    return new_v

def load_pmbody17(file, pm):
    # read bounding box
    size = struct.unpack("<i", file.read(4))[0]
    p1 = struct.unpack("<fff", file.read(12))
    p2 = struct.unpack("<fff", file.read(12))
    p3 = struct.unpack("<fff", file.read(12))
    p4 = struct.unpack("<fff", file.read(12))
    u = struct.unpack("<fff", file.read(12))
    # read bounding box end
    pm.vertexList = list()
    for v in range(pm.faceVertexCount):
        pm.vertexList.append(struct.unpack("<h", file.read(2))[0])
    pm.stripVertexList = list()
    for v in range(pm.stripFaceVertexCount):
        pm.stripVertexList.append(struct.unpack("<h", file.read(2))[0])
    pm.vertexArray = list()
    for v in range(pm.vertCount):
        pm.vertexArray.append(load_vertex(file))
    pm.skinArray = list()
    for s in range(pm.skinCount):
        new_s = Skin()
        new_s.n, new_s.a, new_s.weight, new_s.b = struct.unpack("<iifi", file.read(16))
        pm.skinArray.append(new_s)
    pm.physicsArray = list()
    for s in range(pm.physicsCount):
        pm.physicsArray.append(struct.unpack("<32s", file.read(32)))
    if pm.isAnimated != 0:
        unk = struct.unpack("<i", file.read(4))[0]
        pm.morphFrames = file.read(pm.morphFrameSize)
    return pm

def load_pm17(file):
    pm = MabinogiMesh()
    pm_size, full_name, mesh_name = struct.unpack("<i32s128s", file.read(164))
    pm.bone_name = full_name.strip(b'\0').decode('utf-8', errors='replace')  # todo: refactor bone_name - full_name
    pm.mesh_name = mesh_name.strip(b'\0').decode('utf-8', errors='replace')
    print (pm.mesh_name, pm.bone_name)
    joint_name, state_name, norm_name, color_name = struct.unpack("32s32s32s32s", file.read(128))
    pm.MinorMatrix = load_matrix4x4(file)
    pm.MajorMatrix = load_matrix4x4(file)
    pm.partNo, _, _, texture, is_texture_mapped = struct.unpack("<iii32si", file.read(48))
    pm.texture_name = texture.strip(b'\0').decode('utf-8', errors='replace')
    v = load_vertex(file)
    pm.faceVertexCount, pm.faceCount, pm.stripFaceVertexCount = struct.unpack("<iii", file.read(12))
    pm.stripFaceCount, pm.vertCount, pm.skinCount = struct.unpack("<iii", file.read(12))  # todo: refactor skin - weld
    pm.physicsCount, pm.isAnimated, pm.morphFrameSize, morphFrameCount = struct.unpack("<iiii", file.read(16))
    file.seek(16,1)
    f, faceSize, stripFaceSize, meshSize, skinSize, physicsSize = struct.unpack("<iiiiii", file.read(24))
    pm = load_pmbody17(file, pm)
    return pm

def load_pm20(file, pm_version=2):
    pm = MabinogiMesh()
    pm_size = struct.unpack("<i", file.read(4))[0]
    pm.MinorMatrix = load_matrix4x4(file)
    pm.MajorMatrix = load_matrix4x4(file)
    pm.partNo, unk1, unk2 = struct.unpack("<iii", file.read(12))
    is_texture_mapped = struct.unpack("<i", file.read(4))[0]
    file.seek(36,1)
    pm.faceVertexCount, pm.faceCount, pm.stripFaceVertexCount = struct.unpack("<iii", file.read(12))
    pm.stripFaceCount, pm.vertCount, pm.skinCount = struct.unpack("<iii", file.read(12))
    pm.physicsCount, pm.isAnimated, pm.morphFrameSize, morphFrameCount = struct.unpack("<iiii", file.read(16))
    file.seek(16,1)
    f, faceSize, stripFaceSize, meshSize, skinSize, physicsSize = struct.unpack("<iiiiii", file.read(24))
    pm.bone_name = load_lpstring(file)
    pm.mesh_name = load_lpstring(file)
    joint_name = load_lpstring(file)
    state_name = load_lpstring(file)
    norm_name = load_lpstring(file)
    if pm_version == 3:
        unk_string = load_lpstring(file)
    color_name = load_lpstring(file)
    pm.texture_name = load_lpstring(file)
    print (pm.mesh_name, pm.bone_name)
    pm = load_pmbody17(file, pm)
    return pm


material_dict_root = None

def init_material_dict(root_path):
    global material_dict, material_dict_root
    material_dict = dict()
    material_dict_root = root_path
    for (dirpath, dirnames, filenames) in os.walk(root_path):
        for name in filenames:
            mat_name, ext = os.path.splitext(name)
            # game files mix .dds/.DDS and texture names don't match file case
            if ext.lower() == ".dds":
                material_dict[mat_name.lower()] = os.path.join(dirpath, name)

def find_materials_path(filename, prefs_path):
    """The preference wins; otherwise look for data/material beside the data/gfx the pmg came from."""
    if prefs_path:
        return bpy.path.abspath(prefs_path)
    path = os.path.dirname(os.path.abspath(filename))
    while True:
        candidate = os.path.join(path, "material")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


# Game material definitions, read from material/_define. Each material lists
# the textures that use it and names a render state, which holds the Direct3D 9
# fixed function setup (texture stages, blending, alpha test, culling).
material_defs = None # texture name (lower case) -> material attributes
render_states = None # render state name (lower case) -> render state

def read_define_xml(path):
    raw = open(path, 'rb').read()
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16')
    return raw.decode('utf-8', errors='replace')

def xml_attrs(tag):
    return dict(re.findall(r'(\w+)="([^"]*)"', tag))

def init_material_defs(root_path):
    '''Parse the definitions with regular expressions, since a few of the
    hand edited files aren't well formed XML and the game loads them anyway.'''
    global material_defs, render_states
    material_defs = dict()
    render_states = dict()
    define_path = os.path.join(root_path, "_define")
    for (dirpath, dirnames, filenames) in os.walk(os.path.join(define_path, "render_state")):
        for name in filenames:
            text = read_define_xml(os.path.join(dirpath, name))
            header = re.search(r'<xml\b[^>]*>', text)
            if header is None:
                continue
            rs = xml_attrs(header.group(0))
            for tag in ("Blend", "AlphaTest", "Misc"):
                found = re.search(r'<' + tag + r'\b[^>]*>', text)
                rs[tag] = xml_attrs(found.group(0)) if found else dict()
            rs["stages"] = [xml_attrs(t) for t in re.findall(r'<TssList\s+ColorOp[^>]*>', text)]
            rs["samplers"] = [xml_attrs(t) for t in re.findall(r'<SsList\s+Address[^>]*>', text)]
            render_states[rs.get("Name", name[:-4]).lower()] = rs
    for (dirpath, dirnames, filenames) in os.walk(os.path.join(define_path, "material")):
        for name in filenames:
            text = read_define_xml(os.path.join(dirpath, name))
            header = re.search(r'<xml\b[^>]*>', text)
            if header is None:
                continue
            mat = xml_attrs(header.group(0))
            for texture in re.findall(r'<TextureDesc\s+Name="([^"]*)"', text):
                material_defs[texture.lower()] = mat

def get_light_group():
    '''Node group holding the lighting value used for D3DTA_DIFFUSE, shared by
    every imported material so the overall brightness can be tuned in one place.'''
    group = bpy.data.node_groups.get("Mabinogi Light")
    if group is None:
        group = bpy.data.node_groups.new("Mabinogi Light", 'ShaderNodeTree')
        group.interface.new_socket("Light", in_out='OUTPUT', socket_type='NodeSocketFloat')
        value = group.nodes.new('ShaderNodeValue')
        value.label = "Light"
        # the game's real lighting values aren't in the data; chosen by eye,
        # since 0.5 (Direct3D's usual neutral) washes the "_1x" states out
        value.outputs[0].default_value = 0.25
        output = group.nodes.new('NodeGroupOutput')
        output.location = (200, 0)
        group.links.new(output.inputs[0], value.outputs[0])
    return group

class GameMaterialBuilder:
    '''Rebuilds a render state's texture stages as shader nodes.'''

    def __init__(self, material):
        self.nodes = material.node_tree.nodes
        self.links = material.node_tree.links
        self.x = 0

    def node(self, type, **settings):
        n = self.nodes.new(type)
        for k, v in settings.items():
            setattr(n, k, v)
        n.location = (self.x, -200 * (len(self.nodes) % 6))
        return n

    def connect(self, socket, value):
        if isinstance(value, bpy.types.NodeSocket):
            self.links.new(socket, value)
        elif isinstance(value, float) and hasattr(socket.default_value, '__len__'):
            # a grey value into a colour socket
            socket.default_value = (value, value, value, 1.0)[:len(socket.default_value)]
        else:
            socket.default_value = value

    def color(self, blend, a, b, fac=1.0, clamp=False):
        n = self.node('ShaderNodeMix', data_type='RGBA', blend_type=blend, clamp_result=clamp)
        sockets = {s.identifier: s for s in n.inputs}
        self.connect(sockets['Factor_Float'], fac)
        self.connect(sockets['A_Color'], a)
        self.connect(sockets['B_Color'], b)
        return next(s for s in n.outputs if s.identifier == 'Result_Color')

    def value(self, operation, a, b=0.0, clamp=False):
        n = self.node('ShaderNodeMath', operation=operation, use_clamp=clamp)
        self.connect(n.inputs[0], a)
        self.connect(n.inputs[1], b)
        return n.outputs[0]

    def scale(self, c, k, clamp):
        return self.color('MULTIPLY', c, (k, k, k, 1.0), clamp=clamp)

    def color_op(self, op, a1, a2, diffuse):
        '''D3DTOP_* on colours; a1/a2 are (colour, alpha) pairs.'''
        c1, c2 = a1[0], a2[0]
        if op in ('D3DTOP_MODULATE', 'D3DTOP_MODULATE2X', 'D3DTOP_MODULATE4X'):
            c = self.color('MULTIPLY', c1, c2, clamp=(op == 'D3DTOP_MODULATE'))
            if op != 'D3DTOP_MODULATE':
                c = self.scale(c, 2.0 if op == 'D3DTOP_MODULATE2X' else 4.0, True)
            return c
        if op == 'D3DTOP_ADD':
            return self.color('ADD', c1, c2, clamp=True)
        if op in ('D3DTOP_ADDSIGNED', 'D3DTOP_ADDSIGNED2X'):
            c = self.color('ADD', c1, c2)
            c = self.color('SUBTRACT', c, (0.5, 0.5, 0.5, 1.0), clamp=(op == 'D3DTOP_ADDSIGNED'))
            if op == 'D3DTOP_ADDSIGNED2X':
                c = self.scale(c, 2.0, True)
            return c
        if op == 'D3DTOP_SUBTRACT':
            return self.color('SUBTRACT', c1, c2, clamp=True)
        if op == 'D3DTOP_SELECTARG2':
            return c2
        if op in ('D3DTOP_BLENDDIFFUSEALPHA', 'D3DTOP_BLENDCURRENTALPHA', 'D3DTOP_BLENDTEXTUREALPHA'):
            # arg1 * alpha + arg2 * (1 - alpha)
            alpha = {'D3DTOP_BLENDDIFFUSEALPHA': diffuse[1],
                     'D3DTOP_BLENDCURRENTALPHA': self.current[1],
                     'D3DTOP_BLENDTEXTUREALPHA': self.texture[1]}[op]
            return self.color('MIX', c2, c1, fac=alpha, clamp=True)
        if op == 'D3DTOP_MODULATEALPHA_ADDCOLOR':
            return self.color('ADD', c1, c2, fac=a1[1], clamp=True)
        if op == 'D3DTOP_MODULATEINVALPHA_ADDCOLOR':
            return self.color('ADD', c1, c2, fac=self.value('SUBTRACT', 1.0, a1[1]), clamp=True)
        return c1 # D3DTOP_SELECTARG1 and anything not handled

    def alpha_op(self, op, a1, a2):
        '''D3DTOP_* on alphas, only the operations the game's render states use.'''
        if op in ('D3DTOP_MODULATE', 'D3DTOP_MODULATE2X', 'D3DTOP_MODULATE4X'):
            a = self.value('MULTIPLY', a1, a2, clamp=(op == 'D3DTOP_MODULATE'))
            if op != 'D3DTOP_MODULATE':
                a = self.value('MULTIPLY', a, 2.0 if op == 'D3DTOP_MODULATE2X' else 4.0, clamp=True)
            return a
        if op == 'D3DTOP_ADD':
            return self.value('ADD', a1, a2, clamp=True)
        if op == 'D3DTOP_SELECTARG2':
            return a2
        return a1

    def build(self, mdef, rs, image, gloss_image):
        nodes, links = self.nodes, self.links
        nodes.clear()
        light = self.node('ShaderNodeGroup', node_tree=get_light_group(), label="Light").outputs[0]
        diffuse = (self.node('ShaderNodeCombineColor').outputs[0], 1.0)
        links.new(diffuse[0].node.inputs[0], light)
        links.new(diffuse[0].node.inputs[1], light)
        links.new(diffuse[0].node.inputs[2], light)
        self.x += 200

        # texture coordinates for the gloss/sphere stages: the view space
        # normal mapped onto the texture, i.e. a matcap
        def matcap():
            geometry = self.node('ShaderNodeNewGeometry')
            view = self.node('ShaderNodeVectorTransform', vector_type='NORMAL', convert_from='WORLD', convert_to='CAMERA')
            links.new(view.inputs[0], geometry.outputs['Normal'])
            uv = self.node('ShaderNodeVectorMath', operation='MULTIPLY_ADD')
            links.new(uv.inputs[0], view.outputs[0])
            uv.inputs[1].default_value = (0.5, 0.5, 0.0)
            uv.inputs[2].default_value = (0.5, 0.5, 0.0)
            return uv.outputs[0]

        # Direct3D blends the raw (sRGB encoded) texel values, while Blender
        # decodes textures to linear, so re-encode before the stage maths
        def raw(tex):
            gamma = self.node('ShaderNodeGamma')
            links.new(gamma.inputs['Color'], tex.outputs['Color'])
            gamma.inputs['Gamma'].default_value = 1 / 2.2
            return (gamma.outputs[0], tex.outputs['Alpha'])

        main_node = None
        regs = {'D3DTA_CURRENT': diffuse, 'D3DTA_TEMP': ((0.0, 0.0, 0.0, 1.0), 0.0)}
        samplers = rs.get("samplers", [])
        for i, stage in enumerate(rs["stages"]):
            if stage.get('ColorOp', 'D3DTOP_DISABLE') == 'D3DTOP_DISABLE':
                break
            self.x += 250
            coord = stage.get('TexCoord', 'Vertex')
            sampler = samplers[i] if i < len(samplers) else dict()
            extension = 'EXTEND' if sampler.get('AddressU') == 'D3DTADDRESS_CLAMP' else 'REPEAT'
            if coord == 'Vertex' and i == 0 and image is not None:
                tex = self.node('ShaderNodeTexImage', image=image, extension=extension)
                main_node = tex
                self.texture = raw(tex)
            elif coord in ('Gloss', 'Sphere') and gloss_image is not None:
                tex = self.node('ShaderNodeTexImage', image=gloss_image, extension='EXTEND')
                links.new(tex.inputs[0], matcap())
                self.texture = raw(tex)
            else:
                # no texture to sample (e.g. the shadow map): neutral grey
                self.texture = ((0.5, 0.5, 0.5, 1.0), 1.0)
            self.current = regs['D3DTA_CURRENT']
            args = {'D3DTA_DIFFUSE': diffuse, 'D3DTA_TEXTURE': self.texture,
                    'D3DTA_CURRENT': regs['D3DTA_CURRENT'], 'D3DTA_TEMP': regs['D3DTA_TEMP'],
                    'D3DTA_SPECULAR': ((0.0, 0.0, 0.0, 1.0), 0.0),
                    'D3DTA_TFACTOR': ((0.5, 0.5, 0.5, 1.0), 1.0)}
            def arg(key):
                return args.get(stage.get(key), args['D3DTA_CURRENT'])
            c = self.color_op(stage['ColorOp'], arg('ColorArg1'), arg('ColorArg2'), diffuse)
            a = self.alpha_op(stage.get('AlphaOp'), arg('AlphaArg1')[1], arg('AlphaArg2')[1])
            result = stage.get('ResultArg', 'D3DTA_CURRENT')
            regs[result if result in regs else 'D3DTA_CURRENT'] = (c, a)
        if main_node is not None:
            nodes.active = main_node # what solid view's texture mode shows

        color, alpha = regs['D3DTA_CURRENT']
        # back to linear for Blender
        decode = self.node('ShaderNodeGamma')
        self.connect(decode.inputs['Color'], color)
        decode.inputs['Gamma'].default_value = 2.2
        color = decode.outputs[0]
        if mdef.get('ForceAlphaOpaque') == 'true':
            alpha = 1.0
        self.x += 250
        blend = rs.get('Blend', {})
        src, dest = blend.get('Src', 'D3DBLEND_ONE'), blend.get('Dest', 'D3DBLEND_ZERO')
        if blend.get('Enable') != 'true':
            src, dest = 'D3DBLEND_ONE', 'D3DBLEND_ZERO'
        # result = colour * src + background * dest, as emission plus transparency
        emission = self.node('ShaderNodeEmission')
        self.connect(emission.inputs['Color'], color)
        if src == 'D3DBLEND_SRCALPHA':
            self.connect(emission.inputs['Strength'], alpha)
        elif src in ('D3DBLEND_ZERO', 'D3DBLEND_DESTCOLOR'):
            emission.inputs['Strength'].default_value = 0.0
        dest_color = None
        if dest == 'D3DBLEND_ONE':
            dest_color = (1.0, 1.0, 1.0, 1.0)
        elif dest == 'D3DBLEND_INVSRCALPHA':
            dest_color = self.value('SUBTRACT', 1.0, alpha)
        elif dest == 'D3DBLEND_SRCALPHA':
            dest_color = alpha
        elif dest == 'D3DBLEND_INVSRCCOLOR':
            invert = self.node('ShaderNodeInvert')
            self.connect(invert.inputs['Color'], color)
            dest_color = invert.outputs[0]
        if src == 'D3DBLEND_DESTCOLOR':
            dest_color = color # multiply
        shader = emission.outputs[0]
        blended = dest_color is not None
        if blended:
            transparent = self.node('ShaderNodeBsdfTransparent')
            self.connect(transparent.inputs['Color'], dest_color)
            add = self.node('ShaderNodeAddShader')
            links.new(add.inputs[0], shader)
            links.new(add.inputs[1], transparent.outputs[0])
            shader = add.outputs[0]

        alpha_test = rs.get('AlphaTest', {})
        if alpha_test.get('Enable') == 'true' and alpha_test.get('Func') in ('D3DCMP_GREATER', 'D3DCMP_GREATEREQUAL'):
            ref = int(alpha_test.get('Ref', '0'), 16) / 255.0
            passed = self.value('GREATER_THAN', alpha, ref - (0.001 if alpha_test['Func'] == 'D3DCMP_GREATEREQUAL' else 0.0))
            hidden = self.node('ShaderNodeBsdfTransparent')
            mix = self.node('ShaderNodeMixShader')
            links.new(mix.inputs[0], passed)
            links.new(mix.inputs[1], hidden.outputs[0])
            links.new(mix.inputs[2], shader)
            shader = mix.outputs[0]

        self.x += 250
        output = self.node('ShaderNodeOutputMaterial')
        links.new(output.inputs['Surface'], shader)
        return blended

def build_game_material(material, mdef, rs, image, gloss_image):
    material.use_nodes = True
    blended = GameMaterialBuilder(material).build(mdef, rs, image, gloss_image)
    # D3DCULL_CCW is Direct3D's default back face culling
    material.use_backface_culling = rs.get('Misc', {}).get('CullMode') == 'D3DCULL_CCW'
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = 'BLENDED' if blended else 'DITHERED'
    elif hasattr(material, "blend_method"):
        material.blend_method = 'BLEND' if blended else 'CLIP'


# Mabinogi is Y up with models facing -Z; Blender is Z up with models facing -Y
Y_UP_TO_Z_UP = (mathutils.Matrix.Rotation(math.radians(180), 4, 'Z') @
                mathutils.Matrix.Rotation(math.radians(90), 4, 'X'))

def load_pmg(filename,
             context,
             z_up=True,
             global_scale=0.01,
             game_materials=True):
    '''Read the PMG file.'''
    print (filename)
    name, ext= os.path.splitext(os.path.basename(filename))
    file= open(filename, 'rb')

    try:
        magic, version, head_size, mesh_name, subgroup_count = struct.unpack("<4shi128si", file.read(142))
    except:
        print("Error parsing file header!")
        file.close()
        return
    if magic != b'pmg\x00':
        print("Not a supported file type!")
        file.close()
        return
    if version != 0x0102:
        print("Not a supported version!")
        file.close()
        return

    mesh_count = 0
    pm_subgroups_count = list()
    subgroup_names = list()
    for i in range(subgroup_count):
        subgroup_name, pmCount = struct.unpack("<64si", file.read(68))
        file.seek(0xCC * pmCount, 1)  # skip pm header
        pm_subgroups_count.append(pmCount)
        subgroup_names.append(subgroup_name.split(b'\0')[0].decode('utf-8', errors='replace'))
        mesh_count += pmCount
    print ("mesh count", mesh_count)

    pm_subgroups = list()
    for sg in range(subgroup_count):
        pm = list()
        for i in range(pm_subgroups_count[sg]):
            pm_magic, pm_version = struct.unpack("<4sh", file.read(6))
            if pm_magic != b'pm!\x00':
                print("Not a supported pm type!")
                file.close()
                return
            if pm_version not in (1793, 2, 3):
                print("Not a supported pm version!", pm_version)
                file.close()
                return
            print("reading mesh")
            if pm_version == 1793 : pm.append(load_pm17(file))
            if pm_version == 2 : pm.append(load_pm20(file))
            if pm_version == 3 : pm.append(load_pm20(file, pm_version))
        pm_subgroups.append(pm)

    addon_prefs = context.preferences.addons[__name__].preferences
    materials_path = find_materials_path(filename, addon_prefs.materials_path)
    if materials_path is None:
        print("No material folder found, set one in the addon preferences")
        materials_path = os.path.dirname(filename)
    if material_dict is None or material_dict_root != materials_path:
        init_material_dict(materials_path)
        init_material_defs(materials_path)

    #find if the selected object is a an armature
    bone_space = mathutils.Matrix(((0, 1, 0, 0),
                                   (0, 0, 1, 0),
                                   (1, 0, 0, 0),
                                   (0, 0, 0, 1)))
    armature = None
    sel_ob = None
    edit_bones = dict()
    if len(context.selected_objects) > 0:
        sel_ob = context.selected_objects[0]
        if type(sel_ob.data) == bpy.types.Armature:
            armature = sel_ob.data
            eb = armature.bones
            for i in range(len(eb)):
                bone_id = eb[i].name[eb[i].name.index('__')+3:]
                edit_bones[bone_id] = eb[i]
        else:
            # todo: deselect
            sel_ob.select_set(False)
            print("Selected object isn't armature")
            sel_ob = None
    # one collection per file, next to the armature when importing onto one.
    # Subgroups are variants the game swaps between (hand poses, hair shapes
    # for helmets, weapon positions), so only the first is shown and the rest
    # go in a hidden child collection rather than overlapping it.
    parent_collection = context.collection
    if sel_ob is not None and sel_ob.users_collection:
        parent_collection = sel_ob.users_collection[0]
    file_name = name # name is reused for texture names below
    file_collection = bpy.data.collections.new(file_name)
    parent_collection.children.link(file_collection)
    variants_collection = None

    prev_ob = None
    for sgi in range(len(pm_subgroups)):
        pm = pm_subgroups[sgi]
        if prev_ob is not None:
            prev_ob.select_set(False)
            prev_ob = None
        target_collection = file_collection
        if sgi > 0:
            if variants_collection is None:
                variants_collection = bpy.data.collections.new(file_name + " variants")
                file_collection.children.link(variants_collection)
            target_collection = variants_collection
        for i in range(len(pm)):
            #Add to blender
            print("adding mesh", pm[i].mesh_name)
            bmesh = bpy.data.meshes.new(pm[i].mesh_name)
            #add vertices and triangles
            verts = [(pm[i].vertexArray[v].x, pm[i].vertexArray[v].y, pm[i].vertexArray[v].z) for v in range(pm[i].vertCount)]
            faces = [pm[i].vertexList[v*3:v*3+3] for v in range(pm[i].faceCount)]
            bmesh.from_pydata(verts, [], faces)
            #add materials
            name = pm[i].texture_name
            #image = load_image(name + ".dds", os.path.dirname(filename), recursive=True, place_holder=True)
            if name not in bpy.data.materials:
                print("LOADING TEXTURE ", name)
                if not name:
                    image = None # untextured mesh
                elif name.lower() in material_dict:
                    image = bpy.data.images.load(material_dict[name.lower()], check_existing=True)
                else:
                    print("Texture %s not found" % name)
                    image = load_image(name + ".dds", os.path.dirname(filename), recursive=True, place_holder=True)
                print(image)
                # Create new material
                material = bpy.data.materials.new(name=name)
                # the game's material for this texture, if there is one
                mdef = material_defs.get(name.lower()) if game_materials and name else None
                rs = render_states.get(mdef.get('RenderState', '').lower()) if mdef else None
                if rs is not None:
                    gloss_name = mdef.get('GlossTexture', '').lower()
                    gloss_image = None
                    if gloss_name in material_dict:
                        gloss_image = bpy.data.images.load(material_dict[gloss_name], check_existing=True)
                    build_game_material(material, mdef, rs, image, gloss_image)
                else:
                    material.use_nodes = True
                    # removed in newer Blender versions
                    if hasattr(material, "shadow_method"):
                        material.shadow_method = 'NONE'
                    if hasattr(material, "blend_method"):
                        material.blend_method = 'OPAQUE'
                    # Add mat node
                    bsdf = material.node_tree.nodes["Principled BSDF"]
                    bsdf.inputs['Roughness'].default_value = 0
                    if image is not None:
                        # Add tex node
                        texImage = material.node_tree.nodes.new('ShaderNodeTexImage')
                        texImage.image = image
                        # Link together
                        material.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])
                        material.node_tree.links.new(bsdf.inputs['Alpha'], texImage.outputs['Alpha'])
            else:
                material = bpy.data.materials[name]
                
            bmesh.materials.append(material)
            #add textures
            bmesh.uv_layers.new()
            uvl = bmesh.uv_layers.active.data[:]
            for v in range(pm[i].faceVertexCount):
                idx = pm[i].vertexList[v]
                uvl[v].uv = (pm[i].vertexArray[idx].u, 1-pm[i].vertexArray[idx].v)
                #print(pm[i].vertexArray[idx].u,pm[i].vertexArray[idx].v)
            #for face in bmesh.uv_layers[0].data:
            #    face.image = image
            bmesh.validate()
            bmesh.update()
            ob = bpy.data.objects.new(pm[i].mesh_name + "_subgroup" + str(sgi), bmesh)
            (vector, rot, scale) = pm[i].MinorMatrix.decompose()
            #ob.location = rot * vector
            if sel_ob is not None:
                ob.parent = sel_ob
                ob.parent_type = 'OBJECT'
                bone_M = edit_bones[pm[i].bone_name].matrix_local @ bone_space.inverted()
                # stays in armature space so skinning matches; follows the armature's orientation
                ob.matrix_world = sel_ob.matrix_world @ bone_M @ pm[i].MinorMatrix
            else:
                # applied to the mesh data so the object isn't left rotated/scaled
                conversion = mathutils.Matrix.Scale(global_scale, 4)
                if z_up:
                    conversion = Y_UP_TO_Z_UP @ conversion
                bmesh.transform(conversion)
                ob.matrix_world = conversion @ pm[i].MajorMatrix @ conversion.inverted()
            target_collection.objects.link(ob)
            #add skins
            skinList = list()
            for s in pm[i].skinArray:
                skinList += (s.n,)
            vgroup = ob.vertex_groups.new()
            vgroup.name = "_" + pm[i].bone_name
            vgroup.add(pm[i].vertexList,1.0,'REPLACE')
            if armature is not None:
                bones = dict()
                for bone in armature.bones:
                    bone_name = bone.name[bone.name.index('__')+3:]
                    bones[bone_name] = bone
                if pm[i].bone_name in bones:
                    vgroup.name = bones[pm[i].bone_name].name
                #bone = armature.bones.get('_' + pm[i].bone_name)
                #if bone is None: bone = armature.bones.get('-' + pm[i].bone_name)
                #if bone is not None:
                #    vgroup.name = bone.name
            ob.select_set(True)
            if prev_ob is not None: prev_ob.select_set(True)
            context.view_layer.objects.active = ob
            bpy.ops.object.join()
            bpy.ops.object.mode_set(mode='EDIT')
            # mesh data is only scaled when not imported onto an armature
            bpy.ops.mesh.remove_doubles(threshold=0.1 if sel_ob is not None else 0.1 * global_scale)
            bpy.ops.object.mode_set(mode='OBJECT')
            prev_ob = ob
        if prev_ob is None:
            continue # empty subgroup
        if subgroup_names[sgi]:
            prev_ob.name = "%s_%s" % (file_name, subgroup_names[sgi])
        elif sgi > 0:
            prev_ob.name = "%s_%d" % (file_name, sgi)
        else:
            prev_ob.name = file_name
        prev_ob.data.name = prev_ob.name
        # add armature modifier; a single one, so vertices shared by
        # several groups aren't deformed more than once
        if sel_ob is not None:
            m = prev_ob.modifiers.new("Armature", 'ARMATURE')
            m.object = sel_ob

    if variants_collection is not None:
        # hidden only after the joins above, which need visible objects
        variants_collection.hide_render = True
        def find_layer_collection(layer_collection):
            if layer_collection.collection == variants_collection:
                return layer_collection
            for child in layer_collection.children:
                found = find_layer_collection(child)
                if found is not None:
                    return found
            return None
        layer_collection = find_layer_collection(context.view_layer.layer_collection)
        if layer_collection is not None:
            layer_collection.hide_viewport = True

    file.close()


from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, CollectionProperty, BoolProperty, FloatProperty
from bpy.types import Operator, OperatorFileListElement
class IMPORT_MABINOGI_pmg(Operator, ImportHelper):
    '''Import PMG Operator.'''
    bl_idname= "import.pmg"
    bl_label= "Import PMG"
    bl_description= "Import a Mabinogi Mesh Group file"
    bl_options= {'REGISTER', 'UNDO'}

    #filepath: StringProperty(name="File Path", description="Filepath used for importing the PMG file", maxlen=1024, default="")
    
    filter_glob: StringProperty(
        default = "*.pmg",
        options = {'HIDDEN'},
    )
    
    files: CollectionProperty(
        name='File paths', 
        type=OperatorFileListElement,
    )
    
    directory: StringProperty(subtype='DIR_PATH')

    z_up: BoolProperty(
        name="Convert to Z Up",
        description="Convert from Mabinogi's Y up axis to Blender's Z up. "
                    "Meshes imported onto a selected armature follow the armature's orientation instead",
        default=True,
    )

    scale: FloatProperty(
        name="Scale",
        description="Scale applied to the meshes. "
                    "Meshes imported onto a selected armature follow the armature's scale instead",
        default=0.01,
        min=0.0001,
        soft_max=1.0,
    )

    game_materials: BoolProperty(
        name="Game Materials",
        description="Recreate the game's materials (texture stages, gloss maps, blending) from "
                    "data/material/_define. Off: a plain Principled BSDF with the texture",
        default=True,
    )
    
    def execute(self, context):
        if self.files:
            filepaths = [os.path.join(self.directory, file.name) for file in self.files]
        else:
            filepaths = [self.filepath]
        for filepath in filepaths:
            load_pmg(filepath, context, self.z_up, self.scale, self.game_materials)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm= context.window_manager
        # file dropped onto the window: only ask for the import options
        if self.properties.is_property_set("filepath"):
            return wm.invoke_props_dialog(self)
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty
class IMPORT_MABINOGI_pmg_prefs(AddonPreferences):
    '''Import PMG preferences.'''
    bl_idname = __name__
    
    materials_path: StringProperty(
        name="Path to materials:",
        description="Folder searched for textures. Leave empty to use the data/material folder next to the imported file",
        subtype='DIR_PATH'
    )

    def draw(self, context):
            layout = self.layout
            layout.label(text="Import PMG preferences")
            layout.prop(self, "materials_path")


def menu_func_mabinogi_pmg(self, context):
    self.layout.operator(IMPORT_MABINOGI_pmg.bl_idname, text="Mabinogi Mesh Group (.pmg)")

class VIEW3D_PT_mabinogi_import_pmg(bpy.types.Panel):
    '''Import button in the 3D viewport sidebar's Mabinogi tab.'''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mabinogi"
    bl_label = "Import Mesh Group (.pmg)"
    # no header, so the buttons from each Mabinogi addon stack into one list
    bl_options = {'HIDE_HEADER'}
    bl_order = 1

    def draw(self, context):
        self.layout.operator(IMPORT_MABINOGI_pmg.bl_idname, text="Import Mesh Group (.pmg)", icon='MESH_DATA')

# drag and drop import, Blender 4.2+
if hasattr(bpy.types, "FileHandler"):
    class MABINOGI_FH_pmg(bpy.types.FileHandler):
        bl_idname = "MABINOGI_FH_pmg"
        bl_label = "Mabinogi Mesh Group"
        bl_import_operator = "import.pmg"
        bl_file_extensions = ".pmg"

        @classmethod
        def poll_drop(cls, context):
            from bpy_extras.io_utils import poll_file_object_drop
            return poll_file_object_drop(context)
else:
    MABINOGI_FH_pmg = None

def register():
    from bpy.utils import register_class
    global material_dict
    material_dict = None
    register_class(IMPORT_MABINOGI_pmg)
    register_class(IMPORT_MABINOGI_pmg_prefs)
    register_class(VIEW3D_PT_mabinogi_import_pmg)
    if MABINOGI_FH_pmg is not None:
        register_class(MABINOGI_FH_pmg)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_mabinogi_pmg)


def unregister():
    from bpy.utils import unregister_class
    if MABINOGI_FH_pmg is not None:
        unregister_class(MABINOGI_FH_pmg)
    unregister_class(VIEW3D_PT_mabinogi_import_pmg)
    unregister_class(IMPORT_MABINOGI_pmg)
    unregister_class(IMPORT_MABINOGI_pmg_prefs)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_mabinogi_pmg)

if __name__ == "__main__":
    register()
