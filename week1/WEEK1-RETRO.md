# Learnings for week 1

## Day 1

- in day 1 we learnt about terminal navigation and system inspection, as well as, a deep understanding of PATH, environment variables, Node runtime

We learnt what is teminal navigation, why it is important as well as how we can do it and what are the commands needed for terminal navigation and operations.

Now whenever we put up a command the shell searches through the PATH, one directory after other to find where exactly the command is. 

- Then we came to wahat Environment variables is, we learnt that they are a key - value pair, that are stored by operating system that programs can read at runtime.

they solve two big problems

1) We can avoid hardcoding values inside code. 
2) We can change behavior, without changing code. It is like the single point where we have to change.

to temprorily create a env file we use export, and to make it permanent across terminals we use source ~/ .bashrc

Note: Export, does not create a variable, it marks a variable to be inherited by child process . 

Child process is a process started by another process. 

- Then we came to Node Runtime, where we got to know what a runtime is. So runtime is the complete environment required to execute a program. 

So, node runtime is the runtime reuired to run node program.

### Problems faced 

- The difference between temporary environment variables (export) and persistent ones (.bashrc) was not obvious initially.

- Understanding what a child process is and why environment variables are inherited rather than created required clarification.


## Day 2 
  
- In day 2 we focused on understanding how programs interact with files and the system, instead of just running commands.

We learned the difference between Buffer and Stream.

Buffer reads the entire file into memory at once, which is simple but risky for large files.

Stream reads data in chunks, which is more memory-efficient and suitable for real-world applications.

- Then we moved to asynchronous programming in Node.js. We understood that Node has a single main thread, and non-blocking means long I/O tasks are handled asynchronously so the main thread remains free.

- We learned what it means to block the main thread and why synchronous heavy operations can freeze the application.
- We also learned about Promise.all, which runs multiple async tasks together and waits for all of them to finish without blocking the event loop.

### Problems faced 

- Asynchronous programming felt confusing because code execution order did not always match the order written in the file.

- The idea that Node.js is single-threaded but still handles multiple tasks felt contradictory at first.

- Understanding Promise.all caused confusion, whether it is incorporating parallelism or not.


## Day 3

- In day 3 we focused on **Git mastery and recovery from mistakes**, instead of just basic version control commands.

We created a repository with multiple commits and intentionally introduced a bug in one of the commits to simulate a real failure.

- We learned how to use git bisect to systematically locate the faulty commit by marking good and bad states instead of guessing.

- After identifying the buggy commit, we fixed the issue and used git revert to undo only the faulty commit while preserving commit history.

- We practiced the stash workflow, where changes were temporarily saved using `git stash`, remote updates were pulled, and then the stashed changes were reapplied.

- We also worked with two clones of the same repository, edited the same line in the same file, and resolved a merge conflict by keeping both changes.

### Problems faced

- Using git bisect was confusing initially, especially understanding how Git narrows down commits.

- There was confusion between git revert and git reset, and why revert is safer for shared history.



## Day 4

- In day 4 we focused on understanding HTTP and APIs through investigation, rather than using tools blindly.

We learned how to inspect API behavior using the terminal instead of relying only on Postman.

- We performed DNS lookup and network path tracing using nslookup and traceroute to understand how requests reach a server.

- We used curl to send HTTP requests and inspect verbose responses, including headers, status codes, and pagination parameters.

- We learned how headers act as metadata and control information, and how modifying request headers changes server behavior.

- We explored ETag-based caching and understood how servers respond with 304 Not Modified when the resource has not changed.

- We also built a small Node HTTP server to echo headers, simulate slow responses, and return cache-related headers.

### Problems faced

- Curl output was difficult to read because of the amount of low-level information.


## Day 5

- In day 5 we focused on automation and building safeguards to prevent bad commits from entering the repository.

We created a validation shell script to ensure required project structure exists and that configuration files are valid.

- We integrated ESLint and Prettier to enforce code quality and formatting automatically.

- We added Husky pre-commit hooks so that validation and linting run before every commit and block commits on failure.

- We created build artifacts with timestamps and checksums to simulate a mini CI pipeline.

- We scheduled validation scripts using cron so checks run automatically without manual intervention.

### Problems faced

- Husky was not working because there were 2 initialised git repo. 



