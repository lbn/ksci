import React, { useState, useEffect } from "react";
import {
  ChakraProvider,
  Box,
  Text,
  VStack,
  Grid,
  theme,
  FormControl,
  FormLabel,
  FormHelperText,
  Input,
  Center,
  Button,
  Link,
  Textarea,
  Flex,
  Heading,
  Spacer,
  Badge,
} from "@chakra-ui/react";

import {
  DownloadIcon,
  ExternalLinkIcon
} from "@chakra-ui/icons"

import {
  BrowserRouter as Router,
  Switch,
  Route,
  useParams,
  useHistory,
} from "react-router-dom";
import { ColorModeSwitcher } from "./ColorModeSwitcher";


function Submit() {
  const [image, setImage] = useState("golang:latest");
  const [repo, setRepo] = useState("https://github.com/lbn/ksci");
  const [steps, setSteps] = useState("cd ksci-finaliser\ngo build -o /output/ksci-finaliser\necho done!");
  const [isLoading, setIsLoading] = useState(false);
  const history = useHistory();
  const handleSubmit = event => {
    event.preventDefault();
    setIsLoading(true);
    fetch("/api/job/submit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        "image": image,
        "repo": repo,
        "steps": steps.split("\n"),
      })
    }).then(res => res.json()).then((result) => {
      history.push(`/job/${result.job.job_id}`);
    }, (error) => {
      alert("error", error);
    });
  };
  return <Box>
    <Heading size="md" p={6} textAlign="center">Submit a job to be executed</Heading>
    <form onSubmit={handleSubmit}>
      <VStack spacing={4}>
        <FormControl id="image" isRequired>
          <FormLabel>Docker image</FormLabel>
          <Input type="text" value={image} onChange={event => setImage(event.currentTarget.value)} placeholder="e.g. golang:latest" />
        </FormControl>
        <FormControl id="repo" isRequired>
          <FormLabel>Link to repository</FormLabel>
          <Input type="text" value={repo} onChange={event => setRepo(event.currentTarget.value)} />
          <FormHelperText>This repository will be cloned in the container</FormHelperText>
        </FormControl>
        <FormControl id="steps" isRequired>
          <FormLabel>Pipeline steps</FormLabel>
          <Textarea fontFamily="mono" value={steps} onChange={event => setSteps(event.currentTarget.value)} placeholder="e.g. echo hello && go build" />
        </FormControl>
        <Button colorScheme="blue" type="submit" isLoading={isLoading}>Submit</Button>
      </VStack>
    </form>
  </Box>
}


function Job() {
  const { jobId } = useParams();
  const [status, setStatus] = useState("pending");
  const [job, setJob] = useState({
    repo: "",
    objectIdLogs: null
  });
  const [objectIdLog, setObjectIdLog] = useState(null);
  const [logs, setLogs] = useState(null);
  const colours = {
    pending: "gray",
    running: "yellow",
    succeeded: "green",
    failed: "red"
  };
  const terminatedStatuses = ["succeeded", "failed"];

  async function getJob() {
    return fetch(`/api/job/${jobId}`).then(res => res.json()).then(async (job) => {
      return job;
    }, (error) => {
      // alert("error")
    })
  }
  function getLogs(objectId) {
    return fetch(`/api/object/${objectId}`).then((res) => {
      return res.text().then(logs => {
        return logs.split("\n")
      })
    }, (error) => {
      // alert("error")
    })
  }
  useEffect(() => {
    async function fetchMyAPI() {
      const job = await getJob();
      setObjectIdLog(job.object_id_logs)
      if (terminatedStatuses.includes(job.status)) {
        setLogs(await getLogs(job.object_id_logs));
      }
      setJob(job);
      setStatus(job.status);
    }
    fetchMyAPI();
  }, []);

  useEffect(() => {
    if (status === "successful") {

    }
    const interval = setInterval(async () => {
      if (terminatedStatuses.includes(status)) {
        clearInterval(interval);
        return
      }
      const newStatus = (await getJob()).status;
      if (newStatus !== status) {
        setStatus(newStatus);
      }
    }, 1000);
    return () => {
      clearInterval(interval);
    }
  }, [status]);


  useEffect(() => {
    if (status === "pending") {
      return
    }

    const interval = setInterval(async () => {
      setLogs(await getLogs(objectIdLog));
      if (terminatedStatuses.includes(status)) {
        clearInterval(interval);
        return
      }
    }, 1000);
    return () => {
      clearInterval(interval);
    }
  }, [status, objectIdLog]);
  return <Box>
    <Heading size="md" p={6} textAlign="center">Job status</Heading>
    <VStack align="stretch" spacing={4}>
      <Flex>
        <Box p="2" >
          <Heading size="md">{jobId}</Heading>
          <Link href={job.repo} isExternal value="aa">
            {job.repo} <ExternalLinkIcon mx="2px" />
          </Link>
        </Box>
        <Spacer />
        <VStack p="2">
          <Badge ml="1" colorScheme={colours[status]}>
            {status}
          </Badge>
          <Button as="a" href={`/api/object/${job.object_id_output}?output`} target="blank" leftIcon={<DownloadIcon />} colorScheme="blue" size="sm" disabled={status !== "succeeded"}>Download</Button>
        </VStack>
      </Flex>
      <Box background="black" color="white" fontFamily="mono" borderRadius="lg" p={2} minHeight={10}>
        {logs ? logs.map((line, index) => <Text key={index}>{line}</Text>) : (<Text color="gray">...</Text>)}
      </Box>
    </VStack>
  </Box >
}

function App() {
  return (
    <Router>
      <ChakraProvider theme={theme}>
        <Center>
          <Grid minW="container.md" p={3}>
            <ColorModeSwitcher justifySelf="flex-end" />
            <Heading textAlign="center" p={6} fontSize="5xl">ksci</Heading>
            <Switch>
              <Route path="/job/:jobId"><Job /></Route>
              <Route path="/"><Submit /></Route>
            </Switch>
          </Grid>
        </Center>
      </ChakraProvider>
    </Router>
  );
}

export default App;
