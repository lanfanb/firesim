//See LICENSE for license details.

#include "simif_peek_poke.h"

// #include "plusargs.h"
// #include "bridges/plusargs.h"
// will to fix this include later
#include "/home/centos/firesim/sim/firesim-lib/src/main/cc/bridges/plusargs.h"


#include <iostream>

class PlusargsModule_t: public simif_peek_poke_t
{
public:
  plusargs_t * plusargsinator;
  PlusargsModule_t(int argc, char** argv) {
#ifdef PLUSARGSBRIDGEMODULE_0_PRESENT
    std::cout << "got PLUSARGSBRIDGEMODULE_0_PRESENT\n";
    PLUSARGSBRIDGEMODULE_0_substruct_create;
    std::vector<std::string> args(argv + 1, argv + argc);
    plusargsinator = new plusargs_t(
      this, args,
      PLUSARGSBRIDGEMODULE_0_substruct);

    // plusargsinator->init();

    // for(const auto s: args) {
    //   std::cout<< "ARG:\n";
    //   std::cout << s << "\n";
    // }
    // std::cout << "\n\n";
#endif
  }

  // void reset_with_plusargs() {
  //   constexpr int pulse_length = 5; // copied from default argument of simif_peek_poke_t::target_reset()
  //   poke(reset, 1);
  //   plusargsinator->tick();
  //   this->step(pulse_length, true);
  //   poke(reset, 0);
  // }

  void run() {
    plusargsinator->init();
    uint32_t is_odd = 0;
    target_reset();
    // reset_with_plusargs(); // call this instead of target_reset

    std::cout << "Step " << "-1" << ", " << peek(io_gotPlusargValue) << "\n";
    for (int i = 0 ; i < 8 ; i++) {
      // plusargsinator->tick();
      step(1);

      // auto peekv = peek(io_gotPlusargValue);
      std::cout << "Step " << i << ", " << peek(io_gotPlusargValue) << "\n";
    }
  }
};
