import pyglet
from pyglet.gl import *
import math
import pandas as pd

global window
window = pyglet.window.Window(height=500, width=1000)
global batch
batch = pyglet.graphics.Batch()

@window.event
def on_draw():
    window.clear()
    batch.draw()

class DesVizObject:
    def __init__(self, id, image, batch, group, scale=1, x0=0, y0=0, is_background=False):
        self.id = id
        self.batch = batch
        self.is_background = is_background
        self.sprite = pyglet.sprite.Sprite(image, batch=batch, group=group)
        self.sprite.scale = scale
        self.sprite.update(x0, y0)

        #parameters for the current move
        self.is_moving = False
        self.t0 = 0
        self.duration = 0
        self.x0 = x0
        self.y0 = y0
        self.dx = 0
        self.dy = 0
        self.x1 = 0
        self.y1 = 0
        self.xref = 0
        self.yref = 0
        self.guide_x = 0
        self.guide_y = 0

        #parameters for path based move
        self.path = None
        self.path_duration = 0
        self.current_segment = 0
        self.end_segment = 0
        self.end_aplha = 1
        self.end_x = 0
        self.end_y = 0
        self.path_orient = False
        self.t_i = 0

        #parameters based on master/slave sprites
        self.slaves = []    #list of sprites which are slaves to this sprite
        self.master = None  #slave's reference to the master sprite
        self.master_dx = 0  #this relates to a slave, gives the offset between master and slave origin points
        self.master_dy = 0

    #NOTE: coordinates and time are in terms of animation, not original simulation units 

    def set_guide(self, x, y):
        self.guide_x = x
        self.guide_y = y

    def place(self, x1, y1):    #imediately position object at position x1, y1
        self.xref = x1
        self.yref = y1
        (x_offset, y_offset) = self.calc_guide_offset()
        self.sprite.update(x1+x_offset, y1+y_offset)
    
    def rotate(self, angle):    #imediately rotate sprite around guide point
        self.sprite.rotation = angle
        (x_offset, y_offset) = self.calc_guide_offset()
        self.sprite.update(self.xref+x_offset, self.yref+y_offset)       

    def move(self, x1, y1, t0, t, auto_orient):    #initiate move at time t0 from current location to x1, y1 with move simulation time duration t and timestep dt
        self.is_moving = True
        self.t0 = t0
        self.duration = t
        self.dx = (x1-self.xref) / t
        self.dy = (y1-self.yref) / t
        self.x0 = self.xref
        self.y0 = self.yref
        self.x1 = x1
        self.y1 = y1
        if auto_orient:
            self.sprite.rotation = self.calc_rotation(self.dx, self.dy)
        self.place(self.xref, self.yref)

    def move_on_path(self, path, t0, t, auto_orient, start_current =False, end =1):
        self.path = path
        self.path_orient = auto_orient
        self.end_alpha = end

        #find where along the path we are starting
        self.current_segment = 0
        if start_current:
            for i in range(len(path.segment_lengths)):
                alpha = (self.xref - path.waypoints[i][0])/(path.waypoints[i+1][0] - path.waypoints[i][0])
                if 0 <= alpha and alpha <= 1:
                    y_interp = path.waypoints[i][1] + alpha * (path.waypoints[i+1][1] - path.waypoints[i][1])
                    if abs(y_interp - self.yref) < 1:
                        break       #sprite (x,y) is on line segment within tolerance
            if i < len(path.segment_lengths):
                self.current_segment = i
            else:
                start_current = False
                self.current_segment = 0    #sprite not on path, so just move to start of path
        
        if end == 1:
            self.end_segment = len(path.segment_lengths) - 1
            self.end_x = path.waypoints[-1][0]
            self.end_y = path.waypoints[-1][1]
        else:
            alpha_st = 0
            for i in range(len(path.segment_lengths)):
                alpha_end = alpha_st + path.segment_lengths[i] / path.total_length
                if alpha_st < end and end <= alpha_end:
                    break
                alpha_st = alpha_end
            self.end_segment = i
            self.end_x = path.waypoints[i][0] + (end - alpha_st) * (path.waypoints[i+1][0] - path.waypoints[i][0])
            self.end_y = path.waypoints[i][1] + (end - alpha_st) * (path.waypoints[i+1][1] - path.waypoints[i][1])

        self.path_duration = t
        duration = t * path.segment_lengths[0]/(end*path.total_length)
        self.t_i = t0 + duration
        if not start_current:
            self.place(path.waypoints[0][0], path.waypoints[0][1])
        self.move(path.waypoints[1][0], path.waypoints[1][1], t0, duration, auto_orient)

    def place_on_path(self, path, auto_orient, end =0):
        alpha_st = 0
        if end == 0:
            (x,y) = (path.waypoints[0][0], path.waypoints[0][1])
            segment = 0
        else:
            for i in range(len(path.segment_lengths)):
                alpha_end = alpha_st + path.segment_lengths[i] / path.total_length
                if alpha_st < end and end <= alpha_end:
                    break
                alpha_st = alpha_end
            x = path.waypoints[i][0] + (end - alpha_st) * (path.waypoints[i+1][0] - path.waypoints[i][0])
            y = path.waypoints[i][1] + (end - alpha_st) * (path.waypoints[i+1][1] - path.waypoints[i][1])
            if auto_orient:
                self.sprite.rotation = self.calc_rotation(path.waypoints[i+1][0] - path.waypoints[i][0], path.waypoints[i+1][1] - path.waypoints[i][1])
            self.place(x,y)

    def attach_to(self, master_sprite, master_dx, master_dy):
        self.master = master_sprite
        self.master.slaves.append(self)
        self.master_dx = master_dx
        self.master_dy = master_dy
        self.master.update_slaves()

    def detach(self):
        (x_offset,y_offset) = self.calc_guide_offset()
        self.xref = self.sprite.x - x_offset
        self.yref = self.sprite.y - y_offset
        self.master.slaves.remove(self)
        self.master = None

    def follow_leader(self, leader_sprite):
        self.is_moving = False
        #TODO: this is for rail network type logic
        pass

    def calc_rotation(self, dx, dy):
        if self.dx==0:
            if self.dy >= 0:
                rotation = 0
            else:
                rotation = 180
        else:
            angle = 180/math.pi * math.atan(self.dy/self.dx)
            if self.dx >= 0:
                rotation = 90-angle
            else:
                rotation = 270 - angle
        return rotation
       
    def calc_guide_offset(self):
        if self.guide_x == 0 and self.guide_y == 0:
            return (0,0)
        theta = math.radians(-self.sprite.rotation)
        return(-self.sprite.scale * (self.guide_x * math.cos(theta) - self.guide_y * math.sin(theta)),
               -self.sprite.scale * (self.guide_x * math.sin(theta) + self.guide_y * math.cos(theta)))

    def update_slaves(self):
        m_scale = self.sprite.scale
        m_x = self.sprite.x
        m_y = self.sprite.y
        m_th = math.radians(-self.sprite.rotation)
        for slave in self.slaves:
            s_x = m_x + m_scale*(slave.master_dx * math.cos(m_th) - slave.master_dy * math.sin(m_th))
            s_y = m_y + m_scale*(slave.master_dx * math.sin(m_th) + slave.master_dy * math.cos(m_th))
            slave.sprite.update(x= s_x, y= s_y, rotation= self.sprite.rotation)
            
    def frame_update(self, elapsed, dt):
        if not self.is_moving:
            return
        
        delta_t = elapsed + dt - self.t0
        if self.dx > 0:
            x = min(self.x1, self.x0 + delta_t*self.dx)
        else:
            x = max(self.x1, self.x0 + delta_t*self.dx)
        if self.dy > 0:
            y = min(self.y1, self.y0 + delta_t*self.dy)
        else:
            y = max(self.y1, self.y0 + delta_t*self.dy)
        self.xref = x
        self.yref = y
        (x_offset, y_offset) = self.calc_guide_offset()
        self.sprite.update(x= x+x_offset, y= y+y_offset)

        if len(self.slaves) > 0:
            self.update_slaves()

        #now update move and path status
        if delta_t >= self.duration:
            if self.path == None:
                self.is_moving = False
            else:
                self.current_segment += 1
                if self.current_segment > self.end_segment:
                    self.is_moving = False
                    self.path = None
                    self.current_segment = 0
                else:
                    if self.current_segment == self.end_segment:
                        xy = (self.end_x, self.end_y)
                        if self.end_alpha == 1:
                            dist = self.path.segment_lengths[self.current_segment]
                        else:
                            dist = self.end_alpha * self.path.total_length - sum(self.path.segment_lengths[i] for i in range(self.end_segment))
                    else:
                        xy = (self.path.waypoints[self.current_segment+1][0], self.path.waypoints[self.current_segment+1][1])
                        dist = self.path.segment_lengths[self.current_segment]
                    duration = self.path_duration * dist/(self.end_alpha*self.path.total_length)
                    self.move(xy[0], xy[1], self.t_i, duration, self.path_orient)
                    self.t_i += duration


class DesVizPath:
    def __init__ (self, a_path_id):
        self.path_id = a_path_id
        self.waypoints = []
        self.segment_lengths = []
        self.total_length = 0
    
    def add_waypoint(self, a_x, a_y):
        if len(self.waypoints) > 0:
            d = math.sqrt((a_x - self.waypoints[-1][0])**2 + (a_y - self.waypoints[-1][1])**2)
            self.segment_lengths.append(d)
            self.total_length += d
        self.waypoints.append((a_x, a_y))
        

class DesVizProgressBar:
    def __init__(self, id, x0, y0, Wx, Hy, rotation, color, batch, group):
        self.prog_id = id
        self.x0 = x0
        self.y0 = y0
        self.Wx = Wx
        self.Hy = Hy
        self.rotation = rotation
        self.color = color
        self.batch = batch
        self.group = group

        self.frame = [None]*4
        self.bar = None

        self.master = None      #sprite that the progress bar is attached to
        self.master_dx = 0
        self.master_dy = 0

        self.create_frame()
    
    def create_frame(self):
        self.bar = pyglet.shapes.Rectangle(x= self.x0, y= self.y0, width= self.Wx, height= self.Hy, 
                                            color= (self.color[0],self.color[1],self.color[2],255), batch= self.batch, group= self.group)
        self.bar.rotation = self.rotation
        vertices = [0]*4
        self.get_vertices(vertices)

        for i in range(3):
            self.frame[i] = pyglet.shapes.Line(x= vertices[i][0], y= vertices[i][1], x2= vertices[i+1][0], y2= vertices[i+1][1],
                                               width= 3, color= (0,0,0,255), batch= self.batch, group= self.group)
        self.frame[3] = pyglet.shapes.Line(x= vertices[3][0], y= vertices[3][1], x2= vertices[0][0], y2= vertices[0][1],
                                               width= 3, color= (0,0,0,255), batch= self.batch, group= self.group)

    def get_vertices(self, vertices_list):
        theta = math.radians(-self.bar.rotation)
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        vertices_list[0] = (self.x0, self.y0) ##
        vertices_list[1] = (self.x0 + self.Wx*cos_theta, self.y0 + self.Wx*sin_theta)
        vertices_list[2] = (self.x0 + self.Wx*cos_theta - self.Hy*sin_theta, self.y0 + self.Wx*sin_theta + self.Hy*cos_theta)
        vertices_list[3] = (self.x0 - self.Hy*sin_theta, self.y0 + self.Hy*cos_theta)
        return (cos_theta, sin_theta)

    def update_level(self, level):  #level \in [0,1]
        self.bar.width = level * self.Wx

    def update_position(self, x0, y0, rotation):
        #TODO...
        pass

    #(x_offset, y_offset) gives the offset of the object origin to the progress bar origin
    def attach_to_object(self, obj: DesVizObject, x_offset, y_offset, rotation):
        self.master = obj
        self.master_dx = x_offset
        self.master_dy = y_offset
        self.rotation = rotation

    def update_attached_position(self):
        self.bar.rotation = self.master.sprite.rotation + self.rotation
        theta = math.radians(-self.master.sprite.rotation)
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)        
        x = self.master.sprite.x + self.master.sprite.scale*(self.master_dx*cos_theta - self.master_dy*sin_theta)
        y = self.master.sprite.y + self.master.sprite.scale*(self.master_dx*sin_theta + self.master_dy*cos_theta)
        (self.bar.x, self.bar.y) = (x, y)
        (self.x0, self.y0) = (x,y)
        vertices = [0]*4
        self.get_vertices(vertices)
        for i in range(3):
            (self.frame[i].x, self.frame[i].y) = (vertices[i][0], vertices[i][1])
            (self.frame[i].x2, self.frame[i].y2) = (vertices[i+1][0], vertices[i+1][1])
        (self.frame[3].x, self.frame[3].y) = (vertices[3][0], vertices[3][1])
        (self.frame[3].x2, self.frame[3].y2) = (vertices[0][0], vertices[0][1])        


class DesVizMaster:
    def __init__(self, a_window_width, a_window_height):
        global window
        global batch
        window.height = a_window_height
        window.width = a_window_width
        #window = pyglet.window.Window(height=a_window_height, width=a_window_width)
        self.batch = batch
        self.background = pyglet.graphics.Group(order=0)
        self.foreground = pyglet.graphics.Group(order=1) 
        self.images = {}
        self.all_obj = {}
        self.fore_obj = {}      #subset of all_obj including all foreground objects
        self.labels = {}
        self.x_min = 0
        self.x_scale = 1
        self.y_min = 0
        self.y_scale = 1
        self.sim_unit_per_second = 1
        
        self.elapsed = 0

        self.script = None
        self.current_row = None
        self.script_index = 0

        self.paths = {}
        self.progress_bars = {}

        self.step = 0

    def set_spatial_domain(self, x_min, y_min, x_max, y_max):
        self.x_min = x_min
        self.y_min = y_min
        self.x_scale = window.width/(x_max - x_min)
        self.y_scale = window.height/(y_max - y_min)
    
    def set_anim_speed(self, sim_unit_per_second):
        self.sim_unit_per_second = sim_unit_per_second
    
    def set_script(self, script_fname):
        self.script = pd.read_csv(script_fname)
        self.current_row = self.script.iloc[self.script_index]
    
    def set_paths(self, path_fname):
        df = pd.read_csv(path_fname)
        prev_path = ''
        for index, row in df.iterrows():
            path_id = row['path_id']
            if path_id != prev_path:
                prev_path = path_id
                self.paths[path_id] = DesVizPath(path_id)
            self.paths[path_id].add_waypoint(row['waypt_x'], row['waypt_y'])

    def add_object(self, id, image_fname, scale=1, x0=0, y0=0, is_background=False):
        if id in self.all_obj:
            return
        
        if image_fname not in self.images:
            self.images[image_fname] = pyglet.resource.image(image_fname)
        image = self.images[image_fname]

        if not is_background:
            group = self.foreground
        else:
            group = self.background
        
        new_object = DesVizObject(id, image, self.batch, group, scale, x0, y0, is_background)
        self.all_obj[id] = new_object
        if not is_background:
            self.fore_obj[id] = new_object

    def frame_update(self, dt):
        self.update_animation_actions()
        for id in self.fore_obj:
            self.fore_obj[id].frame_update(self.elapsed, dt)
        for id in self.progress_bars:
            if self.progress_bars[id].master != None:
                self.progress_bars[id].update_attached_position()
        #TODO: attached_pbar_update
        self.elapsed += dt
    
    def run(self, frame_interval):
        pyglet.clock.schedule_interval(self.frame_update, frame_interval)
        pyglet.app.run()

    def update_animation_actions(self):
        if self.script_index >= len(self.script):
            return

        t = self.current_row['time']/self.sim_unit_per_second
        if t > self.elapsed:
            return
        
        while t <= self.elapsed:
            command = self.current_row['command']
            if command == 'speed':
                self.sim_unit_per_second = float(self.current_row['arg1'])
            elif command == 'add':
                self.add_object(id= self.current_row['arg1'], image_fname= self.current_row['arg2'], scale= float(self.current_row['arg3']), 
                                x0= float(self.current_row['arg4']), y0= float(self.current_row['arg5']),
                                is_background= bool(int(self.current_row['arg6'])))
            elif command == 'place':
                self.fore_obj[self.current_row['arg1']].place(float(self.current_row['arg2']), float(self.current_row['arg3']))
            elif command == 'move':
                self.fore_obj[self.current_row['arg1']].move(x1= float(self.current_row['arg2']), y1= float(self.current_row['arg3']),
                                                             t0= t, t= float(self.current_row['arg4'])/self.sim_unit_per_second, 
                                                             auto_orient= bool(int(self.current_row['arg5'])))
            elif command == 'move_on':
                self.fore_obj[self.current_row['arg1']].move_on_path(path= self.paths[self.current_row['arg2']], 
                                                                     t0= t, t= float(self.current_row['arg3'])/self.sim_unit_per_second, 
                                                                     auto_orient= bool(int(self.current_row['arg4'])),
                                                                     start_current= bool(int(self.current_row['arg5'])),
                                                                     end= float(self.current_row['arg6']))
            elif command == 'place_on':
                self.fore_obj[self.current_row['arg1']].place_on_path(path= self.paths[self.current_row['arg2']], 
                                                                     auto_orient= bool(int(self.current_row['arg3'])),
                                                                     end= float(self.current_row['arg4']))
            elif command == "attach":
                master = self.fore_obj[self.current_row['arg2']]
                self.fore_obj[self.current_row['arg1']].attach_to(master, float(self.current_row['arg3']), float(self.current_row['arg4']))
            elif command == "detach":
                self.fore_obj[self.current_row['arg1']].detach()
            elif command == 'delete':
                self.fore_obj[self.current_row['arg1']].sprite.delete()
                del self.fore_obj[self.current_row['arg1']]
                del self.all_obj[self.current_row['arg1']]
            elif command == 'guide':
                self.fore_obj[self.current_row['arg1']].set_guide(float(self.current_row['arg2']), float(self.current_row['arg3']))
            elif command == 'scale':
                self.fore_obj[self.current_row['arg1']].sprite.scale *= float(self.current_row['arg2'])
            elif command == 'visible':
                self.fore_obj[self.current_row['arg1']].sprite.visible = bool(int(self.current_row['arg2']))
            elif command == 'color':
                self.fore_obj[self.current_row['arg1']].sprite.color = (int(self.current_row['arg2']),
                                                                        int(self.current_row['arg3']),
                                                                        int(self.current_row['arg4']))
            elif command == 'rotation':
                self.fore_obj[self.current_row['arg1']].rotate(float(self.current_row['arg2']))
            elif command == 'image':
                image_fname = self.current_row['arg2']
                if image_fname not in self.images:
                    self.images[image_fname] = pyglet.resource.image(image_fname)
                image = self.images[image_fname]
                self.fore_obj[self.current_row['arg1']].sprite.image = image
            elif command == 'text_field':
                label_name = self.current_row['arg1']
                self.labels[label_name] = pyglet.text.Label(self.current_row['arg2'],
                                                            font_name= self.current_row['arg3'],
                                                            font_size= int(self.current_row['arg4']),
                                                            batch= self.batch,
                                                            color=(0,0,0,255),
                                                            x= int(self.current_row['arg5']),
                                                            y= int(self.current_row['arg6']),
                                                            z= 1)
            elif command == 'text':
                self.labels[self.current_row['arg1']].text = self.current_row['arg2']
            elif command == 'text_color':
                self.labels[self.current_row['arg1']].color = (int(self.current_row['arg2']),
                                                                int(self.current_row['arg3']),
                                                                int(self.current_row['arg4']),
                                                                255)
            elif command == 'add_pbar':
                id = self.current_row['arg1']
                new_pbar = DesVizProgressBar(id= id,
                                              x0= float(self.current_row['arg2']),
                                              y0= float(self.current_row['arg3']),
                                              Wx= float(self.current_row['arg4']),
                                              Hy= float(self.current_row['arg5']),
                                              rotation= float(self.current_row['arg6']),
                                              color= (0,0,255,255),
                                              batch= self.batch, group= self.foreground)
                self.progress_bars[id] = new_pbar
            elif command == 'pbar_level':
                pbar = self.progress_bars[self.current_row['arg1']]
                pbar.update_level(float(self.current_row['arg2']))
            elif command == 'pbar_attach':
                pbar = self.progress_bars[self.current_row['arg1']]
                pbar.attach_to_object(obj= self.fore_obj[self.current_row['arg2']], 
                                      x_offset= float(self.current_row['arg3']), 
                                      y_offset= float(self.current_row['arg4']), 
                                      rotation= float(self.current_row['arg5']))
            elif command == 'pbar_color':
                pbar = self.progress_bars[self.current_row['arg1']]
                pbar.bar.color = (int(self.current_row['arg2']),
                                int(self.current_row['arg3']),
                                int(self.current_row['arg4']),
                                255)
            #TODO: pbar attach
            #TODO: pbar delete...
            #TODO: pbar color
            
            #TODO: text_color
            #TODO:
            #TODO: follow           
            
            self.script_index += 1
            if self.script_index >= len(self.script):
                return
            self.current_row = self.script.iloc[self.script_index]
            t = self.current_row['time']/self.sim_unit_per_second