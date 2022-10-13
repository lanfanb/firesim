//See LICENSE for license details.

package firesim.midasexamples

import chisel3._
import freechips.rocketchip.config.Parameters
import chisel3.util._
import chisel3.util.Enum

import midas.widgets._
// import midas.widgets.{RationalClockBridge, PeekPokeBridge}

// import midas.targetutils.SynthesizePrintf

class PlusargsModuleIO(val params: PlusargsBridgeParams) extends Bundle {
  // val msgInCycle = Input(UInt(16.W))  //Cycle when error is valid
  // val validInCycle = Input(UInt(16.W)) //Cycle when the program finishes
  // val doneErrCode = Input(UInt(((params.conditionInfo).size).W)) //Error code supplied by program
  val in  = Input(Bool()) // delme
  val gotPlusargValue = Output(UInt((params.width).W)) // Output value that plusargs bridge gives us
  // val valid = Output(Bool()) // valid signal coming from plusargs bridge
}

class PlusargsDUT extends Module {

  // ----------------------------------------------------------------------
  // val pin = PlusArg("custom_boot_pin", width=1)
  // val endMessage = Seq(TerminationCondition(false, "success 1"), TerminationCondition(false, "success 2"), TerminationCondition(true, "failure 3"))
  
  val params = PlusargsBridgeParams("plusargs_test_value", default = 0, docstring = "", width=32)
  // val params = PlusargsBridgeParams("plusargs_test_value")

  val io = IO(new PlusargsModuleIO(params))
  // val counter = RegInit(0.U(16.W))

  // counter := counter + 1.U 
  // val valid = (io.doneErrCode.asBools).map { _ && (counter >= io.validInCycle)}

  // val bridge = PlusargsBridge(io.gotPlusargValue, params) 
  // apply version 
  // val bridge = PlusargsBridge(params)
  // io.gotPlusargValue := bridge.io.out

  io.gotPlusargValue := PlusargsBridge.drive(params)

}


// // A simple MIDAS harness that generates a legacy
// // module DUT (it has a single io: Data member) and connects all of
// // its IO to a PeekPokeBridge
// class PeekPokeMidasExampleHarness2(dutGen: () => Module) extends RawModule {
//   val clock = RationalClockBridge().io.clocks.head
//   val reset = WireInit(false.B)

//   withClockAndReset(clock, reset) {
//     val dut = Module(dutGen())
//     val peekPokeBridge = PeekPokeBridge(clock, reset, chisel3.experimental.DataMirror.modulePorts(dut).filterNot {
//       case (name, _) => name == "clock" | name == "reset"
//     }:_*)
//   }
// }



// class Plusargs(implicit p: Parameters) extends PeekPokeMidasExampleHarness(() => new ParityDUT)
class Plusargs(implicit p: Parameters) extends PeekPokeMidasExampleHarness(() => new PlusargsDUT)
// class Plusargs(implicit p: Parameters) extends PeekPokeMidasExampleHarness2(() => new PlusargsDUT)
