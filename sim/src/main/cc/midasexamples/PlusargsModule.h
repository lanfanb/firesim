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

    plusargsinator->init();

    // for(const auto s: args) {
    //   std::cout<< "ARG:\n";
    //   std::cout << s << "\n";
    // }
    // std::cout << "\n\n";
#endif

  }
  void run() {
    uint32_t is_odd = 0;
    target_reset();
    for (int i = 0 ; i < 8 ; i++) {
      plusargsinator->tick();
    //   uint32_t bit = rand_next(2);
    //   poke(io_in, bit);
      step(1);
    //   is_odd = (is_odd + bit) % 2;
    //   expect(io_out, is_odd);
    //   expect(1, 1);
        std::cout << "Step " << i << "\n";
    }
  }
};
