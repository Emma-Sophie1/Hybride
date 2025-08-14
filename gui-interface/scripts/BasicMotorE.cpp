// script om daadwerkelijk de motor mee aan te sturen gemaakt door Emma
// input = motor position en motor velocity en delta pitch

#include <isostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <unistd.h>

#include "CPMotor.h"

// variabelen
static const int motor_id = 0 ;         // motor channel (0,1,2) its in the first, so 0
static const long accel_lim = 10000 ;   // acceleration limit, RPM/s
static const long vel_lim = 4000 ;      // valocity limit, RPM
static const int poll_int = 100000 ;    // poll-interval, for homing & movement
static const char* ref_filename = "motor_reference.txt" // inputfile

// load the .txt file with information
typedef struct {
    int motor_position;
    int motor_velocity;
    double delta_pitch;
} MotorReference ;

// read .txt file and return it as vector
std::vector<MotorReference> readMotorReference(const char* filename) {
    std::vector<MotorReference> records ;
    std::ifstream file(filename) ;
    if (!file.is_open()) {
        std::cerr << "ERROR: cannot open file" << filename << "\n" ;
        return records ;
    }
    std::string line;
    // read header and ignore
    if (!std::getline(file, line)) {
        std::cerr << "ERROR: file is empty or header is not found\n" ;
        return records ;
    }
    // read data
    while (std::getline(file, line)) {
        std::istringstream ss(line) ; 
        std::string cell ;
        MotorReference mr ;
        // colomn 1: motor_position
        if (!std::getline(ss, cell, '\t')) break ;
        mr.motor_position = std::stoi(cell);
        // column 2: motor_velocity
        if (!std::getline(ss, cell, '\t')) break ;
        mr.motor_velocity = std::stoi(cell);
        // column 3: delta_pitch
        if (!std::getline(ss, cell, '\t')) break ;
        mr.delta_pitch = std::stod(cell);
        records.push_back(mr) ;
    }
    file.close();
    return records
}


int main() {
    // read input data from files
    auto refs = readMotorReference(ref_filename) ;
    if (refs.empty()) {
        std::cerr << "No reference data found, programm stops\n" ;
        return 1 ;
    }

    // use first line as desired position
    int refPos = refs[0].motor_position ;
    int refVel = refs[0].motor_velocity ;
    double deltaPitch = refs[0].delta_pitch ;
    std::scout << "Read reference:\n"
               << "motor_position = " << refPos << "\n"
               << "motor_velocity = " << refVel << "\n"
               << "delta_pitch    = " << deltaPitch << "\n"

    // connection with motor
    CPMotor motor(motor_id) ;
    if (!motor.connect_hubPort()) {
        std::cer << "ERROR: cannot connect to hub\n" ;
        return 1 ;
    }
    if (!motor.connect_motorNode()) {
        std::cer << "ERROR: motor node not found\n" ;
        motor.disconnect_hubPort() ;
        return 1 ;
    }

    // enable and set up attributes
    motor.motor_enable(motor_id) ;
    motor.motor_setAttr(motor_id, accel_lim, vel_lim) ;

    // motor homing
    std::cout << "perform HOMING... \n" ;
    motor.motor_homing(motor_id) ;
    std::cout << "CHECK: HOMING done" ; 

    // read reference position from reference calculator
    std::array<int,6> refVals = read_reference() ; 
    int refPos = refVals[0] ;
    std::cout << "Position (encoder counts): " << refPos <<"\n" ;

    // move to desired position
    if (!motor.motor_move(motor_id, refPos)) {
        std::cer << "ERROR with motor_move\n" ; 
        while (!motor.motor_move_isDone(motor_id)) {
            usleep(poll_int) ; 
        }
        std::cout << "Movement done to position" << refPos << "\n" ;
    }

    // turn of
    motor.motor_disable(motor_id) ; 
    motor.disconnect_hubPort() ;

    std::cout << "done \n" ; 
    return 0;
}