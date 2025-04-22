# Getting Started with Engramic

Please contact us at info@engramic.org if you have any issues with these instructions.


??? note "1. Pre-Requisites - OS & IDE"
    We are currently testing Engramic on **WSL on Windows** using **Visual Studio Code**. It *may* run on other configurations—we'll begin cross-platform testing soon. If you'd like to help us, please reach out at [info@engramic.org](mailto:info@engramic.org).


??? note "2. Clone or Fork From [GitHub](https://github.com/engramic/engramic)"

    Clone or fork the latest version from the `main` branch of the Engramic GitHub repository:

    📎 [https://github.com/engramic/engramic](https://github.com/engramic/engramic)

    Engramic is availible via pip, however, working directly from the code is recomended at this time.

    ```
    pip install engramic
    ```

    



??? note "3. Install [Hatch](https://hatch.pypa.io/1.12/install/#command-line-installer_1)"

    We use **[Hatch](https://hatch.pypa.io)** as our Python project manager. It handles all dependencies, Python versioning, testing, versioning, scripts, and virtual environments.

    🔗 [Hatch Installation](https://hatch.pypa.io/1.12/install/#command-line-installer_1)

    We recommend using `pipx` as described in the Hatch installation instructions.

    ⚠️ You may see a browser download warning when downloading the Hatch installer.

    Watch a [video](https://www.youtube.com/watch?v=aY4lpy9vV0Q&t=372s) of using Hatch in Engramic.

??? note "4. Initialize the Environment"

    Now that Hatch is installed:

    1. Navigate to the root of the Engramic project in your terminal.
    2. Run:

        ```
        hatch shell
        ```

    This will install all dependencies (should be quick—we work hard to minimize dependencies).

    3. Open the project in VS Code:

        ```
        code .
        ```

    

??? note "5. Configure the Python Interpreter"

    In Visual Studio Code:

    1. Press `Ctrl + Shift + P`
    2. Search for and select **"Python: Select Interpreter"**
    3. Choose the environment that looks like:  
    `Python X.XX.X ('engramic')`



??? note "6. Run the Mock Version"

    ### Running The Code ###

    The code is available at:
    ```
        engramic/examples/mock_profile/mock_profile.py
    ```

    1. Open the **Run and Debug** sidebar in VS Code.
    2. Choose **"Example - Mock"** and run it.

    > You may get a Windows Security warning for Python — that's expected.

    Congrats! 🎉 You've just run the mock version of the system using mock plugins. You Should see the output message in Terminal Window.
    
    ### Looking At The Code ###
    The mock version doesn't actually use AI calls, just emulated API calls that return static responses via the Mock plugins. In this example, you can see how to create a Host, MessageService, RetrieveService, and a ResponseService. Also, we have created a service called TestService whose only job is to recieve the Response call from the subscirbed callback on_main_prompt_complete.



??? note "7. Run the Standard Version"

    ### Running The Code ###

    Now, let's run an example with actual AI. This example uses Google Gemini.

    ```
        engramic/examples/standard_profile/standard_profile.py
    ```

    1. In **Run and Debug**, select **"Example - Standard"**.
    
    2. For this example, you'll need a **Gemini API key**:

        - Create a Google Cloud account if you don't already have one.
        - Follow Google's documentation to create an API key.

    3. Add a `.env` file to the root of the project with the following content:

        ```env
        GEMINI_API_KEY=PUT_YOUR_KEY_HERE_WITH_NO_QUOTES_OR_ANYTHING_ELSE
        ENGRAMIC_PLUGIN_PATHS=/your/absolute/directory/path/engramic/src/engramic/infrastructure/plugins
        LOCAL_STORAGE_ROOT_PATH=/your/absolute/directory/path/engramic/local_storage
        ```

        Locate this line and change it if you would like to.

        ```python
        retrieve_service.submit(Prompt('Briefly tell me about Chamath Palihapitiya.'))
        ```

    ### Looking At The Code ###
    
    Run the program. The plugins will automatically download all dependencies on the first run and check for updates on subsequent runs. Configuration for plugins are defined by [profiles](profiles.md), in this case, the profile is named "standard"

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

    This time, we've added another call to our TestService. Services support manage sync and async threads. Some features that services perform run on the main thread, such as subscribing, while others such as sending messages or running tasks (not demonstrated) must run on the async thread. The Codify service is listening for the SET_TRAINING_MODE call.

    ```
        class TestService(Service):
            def start(self):
                self.subscribe(Service.Topic.MAIN_PROMPT_COMPLETE,on_main_prompt_complete)
                self.subscribe(Service.Topic.OBSERVATION_COMPLETE,on_observation_complete)
                return super().start()
            
            def init_async(self):
                super().init_async()
                self.send_message_async(Service.Topic.SET_TRAINING_MODE,{"training_mode":True})
                return None
    ```

    Let's look the Observation, the output of the Codify service. Two types of data structures are output on the screen, the first is a set of Engrams, these are the memories extracted from the response of the training. The next is the Meta Summary. Meta data are summary information about all Engrams that were generated. This data structure is created to help the retrieval stage with awareness of it's memory set.

    To delete all memories, enter into the hatch shell named "dev".

    ```
    cd /engramic
    hatch shell dev
    hatch run delete_dbs
    ```


    