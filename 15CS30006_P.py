import numpy as np

OPCODE_TO_STRING = {0:"Add",1:"Sub",2:"Mul",3:"Div"}
#OPCODE_SYMBOL = ['+','-','*','/']
OP_CYLES = [2,2,10,40]
NUM_ADD_STNS = 3
NUM_MUL_STNS = 2
NUM_REGISTERS = 8
INSTRUCTION_QUEUE_LIMIT = 10

#Data structure for Reservation Station
class ReservationStattion:
    def __init__(self,res_num):
        self.num = res_num
        self.busy = 0
        self.opcode = None
        self.Vj = None
        self.Vk = None
        self.Qj = None
        self.Qk = None
        self.dispatched = None  #None if RS not dipatched. Otherwise, stores the cycle number in which it was dispatched.

    #To free a RS after it broadcasts its result
    def reset(self):
        self.busy = 0
        self.opcode = None
        self.Vj = None
        self.Vk = None
        self.Qj = None
        self.Qk = None
        self.dispatched = None

#Data structure for an Instruction
class Instruction:
    def __init__(self,opcode,dst,src1,src2):
        self.opcode = opcode
        self.dst = dst
        self.src1 = src1
        self.src2 = src2

    def __str__(self):
        #print("R"+str(self.dst)+"=R"+str(self.src1)+OPCODE_SYMBOL[self.opcode]+"R"+str(self.src2))
        return OPCODE_TO_STRING[self.opcode]+" R"+str(self.dst)+", R"+str(self.src1)+", R"+str(self.src2)


INSTRUCTION_QUEUE = []
REGISTER_FILE = np.zeros(NUM_REGISTERS,dtype=int)
#RAT => -1 means it is not currently associated with any Reservation Station
RAT = np.zeros(NUM_REGISTERS,dtype=int) - 1
RESERVATION_STATIONS = []
for i in range(5):
    rs = ReservationStattion(i)
    RESERVATION_STATIONS.append(rs)

#Finds an appropriate Free RS and return its number. Returns None otherwise
def _get_free_stn(opcode):
    if opcode < 2:  #Add or Subtarct
        free_stn = -1
        for i in range(NUM_ADD_STNS):
            if RESERVATION_STATIONS[i].busy == 0:
                free_stn = i
                break
        if free_stn == -1:
            return None
        else:
            return free_stn
    else:   #Multiply or Divide
        free_stn = -1
        for i in range(NUM_ADD_STNS,NUM_ADD_STNS+NUM_MUL_STNS):
            if RESERVATION_STATIONS[i].busy == 0:
                free_stn = i
                break
        if free_stn == -1:
            return None
        else:
            return free_stn

#Performs the Issue Step. Updates RS if found and returns its number. Returns None otherwise
def issue():
    global INSTRUCTION_QUEUE
    if len(INSTRUCTION_QUEUE) == 0:     #None Instruction Left in the Queue
        return None

    instruction = INSTRUCTION_QUEUE[0]
    free_stn = _get_free_stn(instruction.opcode)
    if free_stn == None:
        return None
    station = RESERVATION_STATIONS[free_stn]
    #station.reset()
    station.busy = 1
    station.opcode = instruction.opcode
    if(RAT[instruction.src1] == -1):    #Get value from RF
        station.Vj = REGISTER_FILE[instruction.src1]
    else:   #Else mark RS
        station.Qj = RAT[instruction.src1]
    if(RAT[instruction.src2] == -1):    #Get value from RF
        station.Vk = REGISTER_FILE[instruction.src2]
    else:   #Else mark RS
        station.Qk = RAT[instruction.src2]
    #Update RAT entry with destination register
    RAT[instruction.dst] = free_stn

    print("Instruction "+str(instruction)+" issued to RS"+str(free_stn))
    INSTRUCTION_QUEUE = INSTRUCTION_QUEUE[1:]   #Pop instruction from Queue
    return free_stn

#Compute the result of operation
def _compute_result(station):
    v1 = station.Vj
    v2 = station.Vk
    op = station.opcode
    if(op==0):
        return v1+v2
    if(op==1):
        return v1-v2
    if(op==2):
        return v1*v2
    if(op==3):
        return int(v1/v2)

#utility function to Broadcast result to all RS
def _broadcast(stn_num,result,captured):
    for i in range(NUM_ADD_STNS+NUM_MUL_STNS):
        station = RESERVATION_STATIONS[i]
        if station.busy == 0:
            continue
        has_cap = False     #To mark if this reservation station has captured any variable
        if station.Qj == stn_num:
            station.Vj = result
            has_cap = True
        if station.Qk == stn_num:
            station.Vk = result
            has_cap = True
        if has_cap:
            captured.append(i)  #Append this RS to the list so that it wont be dispatched in this cycle.

#Boradcasts result if any RS is ready (Multiplication unit Prioritised).
#All the RS capturing the result are stored in the the list 'captured' which is returned by this function.
def broadcast_and_capture(cycle):
    captured = []
    broadcasted = False     #To mark if Multiplication units broadcasts any result
    #First try to broadcast Multiplication Unit
    for i in range(NUM_ADD_STNS,NUM_ADD_STNS+NUM_MUL_STNS):
        station = RESERVATION_STATIONS[i]
        if station.busy == 0:
            continue
        if station.dispatched == None:
            continue
        if cycle >= station.dispatched + OP_CYLES[station.opcode]:  #This station needs to broadcast its result
            result = _compute_result(station)
            print("RS"+str(i)+" broadcasting its result = "+str(result))
            #Update RAT and RF
            for j in range(NUM_REGISTERS):
                if RAT[j] == i:
                    REGISTER_FILE[j] = result
                    RAT[j] = -1
                    break
            #Broadcast Result to Reservation Stations
            _broadcast(i,result,captured)
            #Reset RS (sets busy bit to 0 and clears all other fields)
            station.reset()
            broadcasted = True
            break

    if broadcasted:     #Multiplication unit broadcasted its results, so dont go for Addition Unit.
        return captured

    for i in range(NUM_ADD_STNS):
        station = RESERVATION_STATIONS[i]
        if station.busy == 0:
            continue
        if station.dispatched == None:
            continue
        if cycle >= station.dispatched + OP_CYLES[station.opcode]:  #This station needs to broadcast its result
            result = _compute_result(station)
            print("RS"+str(i)+" broadcasting its result = "+str(result))
            #Update RAT and RF
            for j in range(NUM_REGISTERS):
                if RAT[j] == i:
                    REGISTER_FILE[j] = result
                    RAT[j] = -1
                    break
            #Broadcast Result to Reservation Stations
            _broadcast(i,result,captured)
            #Reset RS (sets busy bit to 0 and clears all other fields)
            station.reset()
            break
    return captured

#Perform Dispatch Step. The RS present in the list not_allowed are ignored as they were either issued in this cycle or captured some variable in this cycle.
def dispatch(cycle,not_allowed):
    #Dispatch Addition Unit
    for i in range(NUM_ADD_STNS):
        if i in not_allowed:
            continue
        station = RESERVATION_STATIONS[i]
        if station.busy == 0:
            continue
        if station.dispatched == None:
            if(station.Vj != None and station.Vk != None):  #Both operands ready
                station.dispatched = cycle  #Mark with the cycle in which it is dispatched.
                print("Dispatched RS"+str(i))
                break
    #Dispatch Multiplication Unit
    for i in range(NUM_ADD_STNS,NUM_ADD_STNS+NUM_MUL_STNS):
        if i in not_allowed:
            continue
        station = RESERVATION_STATIONS[i]
        if station.busy == 0:
            continue
        if station.dispatched == None:  #Both operands ready
            if(station.Vj != None and station.Vk != None):
                station.dispatched = cycle  #Mark with the cycle in which it is dispatched.
                print("Dispatched RS"+str(i))
                break


NUM_INSTR = 0
TOT_CYCLES = 0

#Parse Input file
with open('input.txt') as f:
    all_lines = f.readlines()
    NUM_INSTR = int(all_lines[0])
    TOT_CYCLES = int(all_lines[1])
    for i in range(NUM_INSTR):
        inst = all_lines[i+2]
        if(inst[-1] == '\n'):
            inst = inst[:-1]
        inst = inst.split(" ")
        inst = [int(x) for x in inst]
        instruction = Instruction(inst[0],inst[1],inst[2],inst[3])
        if(len(INSTRUCTION_QUEUE) > INSTRUCTION_QUEUE_LIMIT):
            print("Instruction Queue overloaded, skipping Instruction "+str(instruction))
        INSTRUCTION_QUEUE.append(instruction)
    for i in range(NUM_REGISTERS):
        REGISTER_FILE[i] = int(all_lines[i+2+NUM_INSTR])


#Simulate
for cycle in range(TOT_CYCLES):
    print("Cycle : %d"%(cycle+1))
    reservation_stn = issue()
    captured_stns = broadcast_and_capture(cycle)
    not_allowed = []    #List of all Reservation Stations which cant be dispatched in this cyle.
    if reservation_stn != None:
        not_allowed.append(reservation_stn) #Issue and dispatch cant happen in same cycle
    not_allowed = not_allowed + captured_stns   #Capture and dispatch cant happen in same cycle
    dispatch(cycle,not_allowed)
    print("=======================================================")

#Output
print("=============Writing Output===================")
print("RS \t\tBusy\tOp\tVj\tVk\tQj\tQk\tDisp\t")
for i in range(NUM_ADD_STNS+NUM_MUL_STNS):
    stn = RESERVATION_STATIONS[i]
    op = OPCODE_TO_STRING[stn.opcode] if stn.opcode != None else '--'
    Vj = str(stn.Vj) if stn.Vj != None else '--'
    Vk = str(stn.Vk) if stn.Vk != None else '--'
    Qj = 'RS'+str(stn.Qj) if stn.Qj != None else '--'
    Qk = 'RS'+str(stn.Qk) if stn.Qk != None else '--'
    disp = '0' if stn.dispatched == None else '1'
    print("RS"+str(i)+"\t\t"+str(stn.busy)+"\t"+op+"\t"+Vj+"\t"+Vk+"\t"+Qj+"\t"+Qk+"\t"+disp)

print("-------------------------------------------")
print("  \t\tRF\t\tRAT")
for i in range(NUM_REGISTERS):
    rs = 'RS'+str(RAT[i]) if RAT[i] != -1 else '--'
    print(str(i)+":\t\t"+str(REGISTER_FILE[i])+"\t\t"+rs)
print("-------------------------------------------")
print("Instruction Queue")
for inst in INSTRUCTION_QUEUE:
    print(inst)
