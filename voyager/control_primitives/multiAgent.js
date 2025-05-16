// send a message to another player indicating that the bot has finished its turn
async function sendSignal(bot, username) {
  bot.chat(`[${username} signal]`)
}

// // sleeps until another player executes sendSignal
// async function waitSignal(bot, timeoutDuration = 30000) {  // Default timeout is set to 20 seconds
//   let timeout;

//   const promise = new Promise((resolve, reject) => {
//     function chatHandler(username, message) {
//       if (username !== bot.username && message === '[player signal]') {
//         clearTimeout(timeout);  // Clear the timeout when the desired message is received
//         resolve();  // Resolve the promise
//         bot.removeListener('chat', chatHandler);  // Remove the event listener
//       }
//     }

//     bot.on('chat', chatHandler);  // Use `on` to continuously listen for chat events
//     bot.chat("[waiting signal]")

//     timeout = setTimeout(() => {
//       bot.removeListener('chat', chatHandler);
//       bot.chat("[signal timeout]");
//       resolve()
//     }, timeoutDuration);
//   });

//   await promise;  // Await for either the desired message or a timeout
// }

// run task and sleep until another player executes sendSignal
async function waitSignal(bot, task=null, timeoutDuration = 30000) {
  let timeout;

  // This is the logic for the chat listener, the same as before
  const chatListening = new Promise((resolve, reject) => {
    function chatHandler(username, message) {
      if (username !== bot.username && message === `[${bot.username} signal]`) {
        bot.chat('[signal recieved]')
        clearTimeout(timeout);
        resolve();
        bot.removeListener('chat', chatHandler);
      }
    }

    bot.on('chat', chatHandler);
    bot.chat("[waiting signal]")

    timeout = setTimeout(() => {
      bot.removeListener('chat', chatHandler);
      bot.chat("[signal timeout]");
      resolve()
    }, timeoutDuration);
  });

  let taskExecution;
  if (task) {
    taskExecution = task(bot);
    await Promise.all([chatListening, taskExecution]);
  } else {
    await chatListening;
  }
}