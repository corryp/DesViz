import random as rnd
import simpy
import pandas as pd

from DesVizScript import *

class PMC_anim:
    def __init__(self):
        self.fanim = create_new_DesViz_script_file('pmc_script.csv')
        self.plant_tons = 0
        self.shovel_tons = [0, 0, 0]
        self.queue = [[] for _ in range(4)]  #0 refers to plant
        self.refueling = [[] for _ in range(4)]
        self.scale50 = 0.6
        self.scale20 = 0.5
        self.sprite_ht = 100
        self.server_loc = {}
        self.server_end = {}
    
    def setup_layout(self):
        server_list = ['P','S1','S2','S3']
        df_paths = pd.read_csv('resources/Paths.csv')
        for s in server_list:
            x = df_paths[df_paths['path_id']==s]['waypt_x'].iloc[0]
            y = df_paths[df_paths['path_id']==s]['waypt_y'].iloc[0]
            self.server_loc[s] = (x,y)
            x = df_paths[df_paths['path_id']==s]['waypt_x'].iloc[1]
            y = df_paths[df_paths['path_id']==s]['waypt_y'].iloc[1]
            self.server_end[s] = (x,y)
        write_DesViz_command(self.fanim, 0,'add',['background','resources/backdrop_rd.jpg',1,0,0,1])
        write_DesViz_command(self.fanim, 0, 'text_field', ['plant_label','0 tons','Arial',24,self.server_end['P'][0],self.server_loc['P'][1]+55])
        write_DesViz_command(self.fanim, 0, 'text_field', ['sh_label3','0 tons','Arial',24,self.server_loc['S3'][0],self.server_loc['S3'][1]-75])
        write_DesViz_command(self.fanim, 0, 'text_field', ['sh_label2','0 tons','Arial',24,self.server_loc['S2'][0],self.server_loc['S2'][1]-75])
        write_DesViz_command(self.fanim, 0, 'text_field', ['sh_label1','0 tons','Arial',24,self.server_loc['S1'][0],self.server_loc['S1'][1]-75])
        write_DesViz_command(self.fanim, 0, 'text_color', ['plant_label',255,255,255])
        write_DesViz_command(self.fanim, 0, 'text_color', ['sh_label3',255,255,255])
        write_DesViz_command(self.fanim, 0, 'text_color', ['sh_label2',255,255,255])
        write_DesViz_command(self.fanim, 0, 'text_color', ['sh_label1',255,255,255])        
        write_DesViz_command(self.fanim, 0, 'add_pbar', ['plant_pbar',self.server_end['P'][0],self.server_loc['P'][1]+30,100,20,0])
        write_DesViz_command(self.fanim, 0, 'add_pbar', ['sh_pbar3',self.server_loc['S3'][0],self.server_loc['S3'][1]-50,100,20,0])
        write_DesViz_command(self.fanim, 0, 'add_pbar', ['sh_pbar2',self.server_loc['S2'][0],self.server_loc['S2'][1]-50,100,20,0])
        write_DesViz_command(self.fanim, 0, 'add_pbar', ['sh_pbar1',self.server_loc['S1'][0],self.server_loc['S1'][1]-50,100,20,0])
    
    def add_trucks(self,truck_list):
        for truck in truck_list:
            write_DesViz_command(self.fanim, 0, 'add', [truck.name,'resources/truckF.png',1,0,0,0])
            if truck.capacity == 20:
                write_DesViz_command(self.fanim, 0, 'scale', [truck.name,self.scale20])
                scale = self.scale20
            else:
                write_DesViz_command(self.fanim, 0, 'scale', [truck.name,self.scale50])
                scale = self.scale50
            write_DesViz_command(self.fanim, 0, 'guide', [truck.name, 25,50])
            write_DesViz_command(self.fanim, 0, 'rotation', [truck.name,90])
            write_DesViz_command(self.fanim, 0, 'add_pbar', [truck.name+'pb',0,0,scale*100,10,0,0])
            write_DesViz_command(self.fanim, 0, 'pbar_attach', [truck.name+'pb',truck.name,65,0,-90])
            write_DesViz_command(self.fanim, 0, 'pbar_color', [truck.name+'pb',150,0,0])

    def move_truck(self, env, truck, duration, is_full, f0, f1):
        time = env.now
        if is_full:
            write_DesViz_command(self.fanim, time, 'image', [truck.name,'resources/truckF.png'])
            write_DesViz_command(self.fanim, time, 'move_on', [truck.name,'S'+str(truck.shovel_num)+'toPq',duration,1,0,1])
            self.shovel_tons[truck.shovel_num-1] += truck.capacity
            write_DesViz_command(self.fanim, time, 'text', ['sh_label'+str(truck.shovel_num),
                                                             str(self.shovel_tons[truck.shovel_num-1])+' tons'])
        else:
            write_DesViz_command(self.fanim, time, 'image', [truck.name,'resources/truckE.png'])
            write_DesViz_command(self.fanim, time, 'move_on', 
                                  [truck.name,'PtoS'+str(truck.shovel_num)+'q',duration,1,0,1])
            self.plant_tons += truck.capacity
            write_DesViz_command(self.fanim, time, 'text', ['plant_label', str(self.plant_tons)+' tons'])
        env.process(self.defuel(env, truck, f0, f1, duration))

    def defuel(self, env, truck, f0, f1, duration):
        if f0 == f1:
            return
        steps = 4
        dt = duration / steps
        df = (f0 - f1) / steps
        for i in range(1,steps+1):
            write_DesViz_command(self.fanim, env.now, 'pbar_level',
                                  [truck.name+'pb',f0 - i*df])
            yield env.timeout(dt)

    def refuel(self, env, truck, duration, f0):
        refuel_list = self.refueling[truck.shovel_num]
        if len(refuel_list) == 0:
            x = self.server_loc["S"+str(truck.shovel_num)][0] - 50
        else:
            x = refuel_list[-1].refuel_x_end
        y = self.server_loc["S"+str(truck.shovel_num)][1] - 50
        write_DesViz_command(self.fanim, env.now, 'place', [truck.name,x,y])
        refuel_list.append(truck)

        if truck.capacity == 20:
            scale = self.scale20
        else:
            scale = self.scale50
        truck.refuel_x_end = x - scale*self.sprite_ht

        steps = 20
        dt = duration / steps
        df = (1 - f0)/steps
        for i in range(1,steps+1):
            write_DesViz_command(self.fanim, env.now, 'pbar_level',
                                  [truck.name+'pb',f0 + i*df])
            yield env.timeout(dt)     
        refuel_list.remove(truck)       

    def service_truck(self, env, truck, time, duration, is_full):
        if is_full:
            self.queue[0].remove(truck)
            write_DesViz_command(self.fanim, time, 'move_on', [truck.name,'P',duration,1,0,1])
            env.process(self.pbar_update(env,duration,'plant_pbar',1))
            self.place_queue(time, 0)
        else:
            self.queue[truck.shovel_num].remove(truck)
            write_DesViz_command(self.fanim, time, 'move_on', [truck.name,'S'+str(truck.shovel_num),duration,1,0,1])
            env.process(self.pbar_update(env,duration,'sh_pbar'+str(truck.shovel_num),0))
            self.place_queue(time, truck.shovel_num)

    def pbar_update(self, env, duration, id, reverse): #this is a process
        steps = 20
        dt = duration/steps
        write_DesViz_command(self.fanim, env.now, 'pbar_level', [id,reverse])
        for i in range(1,steps+1):
            yield env.timeout(dt)
            if reverse:
                write_DesViz_command(self.fanim, env.now, 'pbar_level', [id,1.0-i/steps])
            else:
                write_DesViz_command(self.fanim, env.now, 'pbar_level', [id,float(i)/steps])

    def update_queue(self, truck, time, q_num):
        self.queue[q_num].append(truck)
        if len(self.queue[q_num]) > 0:
            self.place_queue(time, q_num)
    
    def place_queue(self, time, q_num):
        if len(self.queue[q_num])==0:
            return
        truck = self.queue[q_num][0]
        if truck.capacity == 20:
            scale = self.scale20
        else:
            scale = self.scale50

        offset = scale * self.sprite_ht
        if q_num == 0:
            write_DesViz_command(self.fanim, time, 'place', 
                                  [truck.name,self.server_loc["P"][0],self.server_loc["P"][1]])
            x = self.server_loc["P"][0] + offset
            y = self.server_loc["P"][1]
        else:
            write_DesViz_command(self.fanim, time, 'place', 
                                  [truck.name,self.server_loc["S"+str(q_num)][0],self.server_loc["S"+str(q_num)][1]])
            x = self.server_loc["S"+str(q_num)][0] - offset
            y = self.server_loc["S"+str(q_num)][1]
        
        offset *= 0.5
        for i in range(len(self.queue[q_num])):
            truck = self.queue[q_num][i]
            write_DesViz_command(self.fanim, time, 'place', [truck.name,x,y])
            if truck.capacity == 20:
                scale = self.scale20
            else:
                scale = self.scale50

            offset += scale * self.sprite_ht / 2
            if q_num == 0:
                x += offset
            else:
                x -= offset
            
            offset = scale * self.sprite_ht / 2

global anim
anim = PMC_anim()

class Truck:
    def __init__(self, env, name,
                 shovel_num, shovel, crusher,
                 load_a, load_b, travel_a, travel_b, unload_a, unload_b,
                 capacity, priority):
        self.env = env
        self.name = name
        self.shovel_num = shovel_num
        self.shovel = shovel
        self.crusher = crusher
        self.load_a = load_a
        self.load_b = load_b
        self.travel_a = travel_a
        self.travel_b = travel_b
        self.unload_a = unload_a
        self.unload_b = unload_b
        self.capacity = capacity
        self.priority = priority

        self.tons_crushed = 0
        self.fuel = 1

        self.refuel_x_end = 0
        
        self.process = env.process(self.truck_process())

    def truck_process(self):
        global anim
        cycle = 0
        while True:
            cycle += 1
            self.print_event(cycle,'ready to load')

            #request shovel and wait until front of queue and shovel ready
            req = self.shovel.request()
            anim.update_queue(self, env.now, self.shovel_num)
            yield req

            #delay for loading
            self.print_event(cycle,'start loading')
            duration = self.load_a + rnd.random()*self.load_b
            anim.service_truck(env, self, env.now, duration, False)
            yield self.env.timeout(duration)
            self.print_event(cycle,'end loading')
            self.shovel.release(req)

            #delay for travel to crusher
            duration = self.travel_a + rnd.random()*self.travel_b
            end_fuel = max(0, self.fuel - 0.1 * duration / self.travel_a)
            anim.move_truck(env, self, duration, True, self.fuel, end_fuel)
            self.fuel = end_fuel
            yield self.env.timeout(duration)            
            self.print_event(cycle,'ready to unload')
            
            #request crusher and wait until front of queue and crusher ready
            req = self.crusher.request(self.priority)
            anim.update_queue(self, env.now, 0)
            yield req

            #delay for unloading
            self.print_event(cycle,'start unloading')
            duration = self.unload_a +rnd.random()*self.unload_b
            anim.service_truck(env, self, env.now, duration, True)
            yield self.env.timeout(duration)
            self.print_event(cycle,'end unloading')
            self.crusher.release(req)

            #update total tons crushed
            self.tons_crushed += self.capacity

            #delay for travel to shovel
            duration = self.travel_a + rnd.random()*self.travel_b
            end_fuel = max(0, self.fuel - 0.1 * duration / self.travel_a)
            anim.move_truck(env, self, duration, False, self.fuel, end_fuel)
            self.fuel = end_fuel
            yield self.env.timeout(duration)

            if self.fuel < 0.2:
                duration = 3 * self.load_a
                self.env.process(anim.refuel(env, self, duration, self.fuel))
                yield self.env.timeout(duration)
                self.fuel = 1

    def print_event(self, cycle_num, event):
        if PRINT_ALL:
            print(str(round(self.env.now,2)) +','+ str(self.shovel_num) +','+ self.name +','+ str(cycle_num) +','+ event)

#settings
SIM_END = 1000
PRIORITY_50t = 0   #0=>higher priority, 1=>equal priority to 20t trucks
PRINT_ALL = False      #set to False to surpress verbose printing

if PRINT_ALL:
    print ("time,shovel,truck,cycle,event")  #headings for output log

#initialise simulation objects
#DesViz = DesVizMaster(1500, 750)
#DesViz.set_paths('resources/Paths.csv')
#anim_master = DesViz
anim.setup_layout()

env = simpy.Environment()

shovels = []     #store references to the 3 shovel Resource objects in a list
shovels.append(simpy.Resource(env, 1))
shovels.append(simpy.Resource(env, 1))
shovels.append(simpy.Resource(env, 1))

crusher = simpy.PriorityResource(env,1)

#convenient to specify travel times using lists of tuples, since travel time varies by shovel
travel20 = [(2.5,0.5),(1.5,0.3),(2,0.4)]
travel50 = [(2.6,0.6),(1.6,0.4),(2.1,0.5)]

trucks = []  #store references to all the Truck objects in a list
for i in range(len(shovels)):  #for each shovel in the list, create 3 trucks assigned to that shovel
    name = "truck20-" + str(i+1) +"1"
    trucks.append(Truck(env, name, i+1, shovels[i], crusher, 3.5, 1.5, travel20[i][0], travel20[i][1], 2, 0.5, 20, 1))
    name = "truck20-" + str(i+1) +"2"
    trucks.append(Truck(env, name, i+1, shovels[i], crusher, 3.5, 1.5, travel20[i][0], travel20[i][1], 2, 0.5, 20, 1))
    name = "truck50-" + str(i+1) +"3"    
    trucks.append(Truck(env, name, i+1, shovels[i], crusher, 8.0, 2.0, travel50[i][0], travel50[i][1], 4, 1, 50, PRIORITY_50t))

anim.add_trucks(trucks)

#run simulation
env.run(until = SIM_END)

#show simulation results
total_tons = sum (tr.tons_crushed for tr in trucks)

print("TOTAL TONS =", total_tons)
print("TONS/HR =", total_tons / (SIM_END/60.0))

anim.fanim.close()

#DesViz.set_script('pmc_script.csv')
#DesViz.run(1 / 60.0)
