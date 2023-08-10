def create_new_DesViz_script_file(fname):
    fscript = open(fname,'w')
    fscript.write('time,command,arg1,arg2,arg3,arg4,arg5,arg6,arg7\n')
    return fscript

def write_DesViz_command(fscript, time, command, arg_list):
    fscript.write(str(time)+','+command)
    for arg in arg_list:
        fscript.write(','+str(arg))
    fscript.write('\n')