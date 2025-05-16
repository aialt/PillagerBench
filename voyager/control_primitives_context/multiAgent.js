// send a message to another player indicating that the bot has finished its turn
async function sendSignal(bot, username) {
  bot.chat(`[${username} signal]`)
}

// run task and sleep until another player executes sendSignal
async function waitSignal(bot, task=null, timeoutDuration = 30000) {
  // This is a promise that will resolve when the bot receives a signal in chat
  const chatListening = new Promise((resolve, reject) => {
    ...
  });

  let taskExecution;
  if (task) {
    taskExecution = task(bot);
    await Promise.all([chatListening, taskExecution]);
  } else {
    await chatListening;
  }
}

// Example usage:
// Suppose you want to alterate task1 and task2 with another player
/*
async function task1() {
  console.log("Starting task1...");
  await new Promise(r => setTimeout(r, 5000)); // Simulate a 5 second task
  sendSignal(bot, "player2");
}
async function task2() {
  console.log("Starting task2...");
  await new Promise(r => setTimeout(r, 5000)); // Simulate a 5 second task
  sendSignal(bot, "player1");
}
// Player 1 code
async function player1() {
  await waitSignal(bot, task1);
  await waitSignal(bot, task2);
}
// Player 2 code
async function player2() {
  await waitSignal(bot, task2);
  await waitSignal(bot, task1);
}
*/