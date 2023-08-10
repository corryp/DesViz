import DesViz

dv = DesViz.DesVizMaster(1500, 750)
dv.set_paths('resources/Paths.csv')
dv.set_script('pmc_script.csv')
dv.set_anim_speed(2)
dv.run(1 / 60.0)

