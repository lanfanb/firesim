#ifdef PLUSARGSBRIDGEMODULE_struct_guard

#include "plusargs.h"
#include <iostream>

plusargs_t::plusargs_t(
  simif_t* sim, 
  std::vector<std::string> &args,
  PLUSARGSBRIDGEMODULE_struct * mmio_addrs): 
    bridge_driver_t(sim), 
    mmio_addrs(mmio_addrs)
{
  //tick-rate to decide sampling rate of MMIOs per number of ticks
  // std::string tick_rate_arg = std::string("+plusargs_test_value=");
  // for (auto &arg: args) {
  //   std::cout << arg << "\n";
  //   if (arg.find(tick_rate_arg) == 0) {
  //     char *str = const_cast<char*>(arg.c_str()) + tick_rate_arg.length();
  //     uint64_t tick_period = atol(str);
  //     this->tick_rate = tick_period;
  //   }
  // }
}

plusargs_t::~plusargs_t() {
  free(this->mmio_addrs);
}

void plusargs_t::tick() {
}

const char* plusargs_t::exit_message() {
    return "";
}

void plusargs_t::init() {
    std::cout << "plusargs_t::init()\n";
    // write(this->mmio_addrs->out, 63);
    write(this->mmio_addrs->out, default_value);
    write(this->mmio_addrs->initDone, 1);
}

#endif
