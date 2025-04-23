# Getting Started with Engramic

Please contact us at info@engramic.org if you have any issues with these instructions.


??? note "1. Pre-Requisites - OS & IDE"
    We are currently testing Engramic on **WSL on Windows** using **Visual Studio Code** With Ubuntu 24.0.1 LTS. It *may* run on other configurations—we'll begin cross-platform testing soon. If you'd like to help us, please reach out at [info@engramic.org](mailto:info@engramic.org).

    Engramic is availible via pip, however, working from source is recommended for this release.

    ```
    pip install engramic
    ```

    To set up your dev environment, you will need the following:
    - Python 3.10+
    - Visual Studio Code
    - Git
    - Pipx
    - Hatch
    - MS VS Code WSL Extension
    - MS Python Debugger
    - Google Gemini API key (optional)


??? note "2. Clone or Fork From [GitHub](https://github.com/engramic/engramic)"

    Clone or fork the latest version from the `main` branch of the Engramic GitHub repository:

    📎 [https://github.com/engramic/engramic](https://github.com/engramic/engramic)



??? note "3. Install [Hatch](https://hatch.pypa.io/1.12/install/#command-line-installer_1)"

    We use **[Hatch](https://hatch.pypa.io)** as our Python project manager. It handles all dependencies, Python versioning, testing, versioning, scripts, and virtual environments.

    🔗 [Hatch Installation](https://hatch.pypa.io/1.12/install/#command-line-installer_1)

    We recommend installing with `pipx` as described in the Hatch installation instructions. Restart your terminal after running pipx ensurepath.

??? note "4. Initialize the Environment"

    Now that Hatch is installed:

    1. Navigate to the root of the Engramic project in your terminal.
    2. Run:

        ```
        hatch env create
        ```

        Enter into the default shell ("default" has no name after "shell".)
        ```
        hatch shell
        ```

    This will install all dependencies (should be quick—we work hard to minimize dependencies).
    Watch a [video](https://www.youtube.com/watch?v=aY4lpy9vV0Q&t=372s) of Hatch in Engramic.

    3. Open Visual Studio Code and install the WSL extension.

    4. Launch VS Code from the WSL terminal:

        ```
        code .
        ```

    4. In Windows, in VS Code, install the Python Debugger extension from Microsoft.
    

??? note "5. Configure the Python Interpreter"

    In Visual Studio Code:

    1. Press `Ctrl + Shift + P`
    2. Search for and select **"Python: Select Interpreter"**
    3. Choose the environment that looks like:  
    `Python X.XX.X ('engramic')`

    Note: If you aren't sure of the path, you can type the following while in the hatch shell:

    ```
    python -c "import sys;print(sys.executable)"
    ```

    If you are stuck, make sure your top, middle search bar in VS Code reads: engramic [WSL: Ubuntu-24.04] (or your distro). If not, your issue is probably related to the WSL extension.

??? note "6. Run the Mock Example"

    ### Running The Code ###

    The code is available at:
    ```
        engramic/examples/mock_profile/mock_profile.py
    ```

    1. Open the **Run and Debug** sidebar in VS Code.
    2. Choose **"Example - Mock"** and run it.

    Congrats! 🎉 You've just run the mock version of the system using mock plugins. You should see an output message in terminal window.
    
    ### Looking At The Code ###
    The mock version doesn't actually use AI calls, just emulated API calls that return static responses via the Mock plugins. In this example, you can see how to create a Host, MessageService, RetrieveService, and a ResponseService. Also, we have created a service called TestService whose only job is to recieve the Response call from the subscirbed callback on_main_prompt_complete.


??? note "7. Run the Standard Example"

    ### Running The Code ###

    Now, let's run an example with actual AI. This example uses Google Gemini.

    ```
        engramic/examples/standard_profile/standard_profile.py
    ```
    
    1. For this example, you'll need a **Gemini API key**:

        - Create a Google Cloud account if you don't already have one.
        - Follow Google's documentation to create a Generative Language API key.

    2. Add a `.env` file to the root of the project with the following content (multiple plugin paths coming soon.):

        ```env
        GEMINI_API_KEY=PUT_YOUR_KEY_HERE_WITH_NO_QUOTES_OR_ANYTHING_ELSE
        LOCAL_STORAGE_ROOT_PATH=./local_storage
        ```

        Locate this line and change it if you would like to.

        ```python
        retrieve_service.submit(Prompt('Briefly tell me about Chamath Palihapitiya.'))
        ```

    3. In **Run and Debug**, select **"Example - Standard"**.

        *Note: this takes some time on first run. Be patient.*


    ### Looking At The Code ###
    
    Run the program. The plugins will automatically download all dependencies on the first run and check for updates on subsequent runs. Configuration for plugins are defined by [profiles](profiles.md), in this case, the profile is named "standard". Each plugin contains it's dependencies in a plugin.toml file.

    Hit **Run** and you'll see the result in the terminal window. This example adds Storage, Codify, and Consolidate service, but doesn't actually use them.
    
    Let's try those services in the next demo.

??? note "8. Create your First Memory."

    ### Running The Code ###

    Let's generate our first memory.

    ```
        engramic/examples/create_memory/create_memory.py
    ```

    1. Run and Debug the profile named "Example - Create Memory".

    You should see three outputs, Response, Meta Summary, and Engrams.

    ### Looking at The Code ###

    This time, we've added another call to our TestService. Services support sync and async threads. Some features that services perform run on the main thread, such as subscribing, while others such as sending messages or running tasks must run on the async thread. The Codify service is listening for the SET_TRAINING_MODE call sent by TestService.

    ```
        class TestService(Service):
            def start(self):
                self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE, self.on_main_prompt_complete)
                self.subscribe(Service.Topic.OBSERVATION_COMPLETE, self.on_observation_complete)

                async def send_message() -> None:
                    self.send_message_async(Service.Topic.SET_TRAINING_MODE, {'training_mode': True})

                self.run_task(send_message())

                super().start()
    ```

    Let's look at the Observation, the output of the Codify service. Two types of data structures are output on the screen, the first is a set of Engrams, these are the memories extracted from the response of the training. The next is the Meta Summary. Meta data are summary information about all Engrams that were generated. This data structure is created to help the retrieval stage with awareness of it's memory set.

    To delete all memories, enter into the hatch shell named "dev".

    ```
    cd /engramic
    hatch shell dev
    hatch run delete_dbs
    ```


    