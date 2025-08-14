#include <iostream>
#include <fstream>
#include <json.hpp>

using json = nlohmann::json;

int main() {
    std::ifstream file("config.json");
    if (!file.is_open()) {
        std::cerr << "Failed to open config.json" << std::endl;
        return 1;
    }

    json config;
    file >> config;

    // Access values
    int endmotor_angle = config["endmotor_angle"];
    int max_motor = config["max_motor"];
    std::vector<int> qh_presets = config["qh_presets"];

    std::cout << "Endmotor Angle: " << endmotor_angle << std::endl;
    std::cout << "Max Motor: " << max_motor << std::endl;
    std::cout << "QH Presets: ";
    for (int val : qh_presets) {
        std::cout << val << " ";
    }
    std::cout << std::endl;

    return 0;
}

