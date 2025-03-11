// Copyright Axis Communications AB.
//
// For a full list of individual contributors, please see the commit history.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
package bindings

/*
#include <stdlib.h>
#include <stdint.h>
*/
import "C"

import (
	"log/slog"
	"os"
	"runtime/cgo"

	"github.com/eiffel-community/etos-library/pkg/stream"
)

// StreamHandler is a struct that holds the logger, connection string, stream name, streamer,
// publisher, and consumer.
// It is used to create a new publisher and publish messages to a stream from python.
// For using the streamers in Go code please refer to pkg/stream/stream.go.
//
// For usage examples view the python code in src/etos_lib/messaging/publisher.py.
type StreamHandler struct {
	logger           *slog.Logger
	connectionString string
	streamName       string
	streamer         stream.Streamer
	publisher        stream.Publisher
	consumer         stream.Consumer
}

// New creates a new publisher and returns a pointer to it.
//
//export New
func New(connectionString, streamName *C.char) (C.uintptr_t, bool) {
	logger := newLogger()
	streamer, err := stream.NewRabbitMQStreamer(C.GoString(streamName), C.GoString(connectionString), logger)
	if err != nil {
		return C.uintptr_t(0), false
	}
	return C.uintptr_t(cgo.NewHandle(&StreamHandler{
		logger:   logger,
		streamer: streamer,
	})), true
}

// Publisher creates a new publisher and starts it.
//
//export Publisher
func Publisher(p C.uintptr_t, name *C.char) bool {
	h := cgo.Handle(p)
	handler, ok := h.Value().(*StreamHandler)
	if !ok {
		// Creating a new logger here since if handler is nil, we don't have access to one.
		newLogger().Error("Failed to get stream handler from memory")
		return false
	}
	publisher, err := handler.streamer.Publisher(C.GoString(name))
	if err != nil {
		handler.logger.Error("Failed to create publisher", slog.Any("Error", err))
		return false
	}
	handler.publisher = publisher
	if err = publisher.Start(); err != nil {
		handler.logger.Error("Failed to start publisher", slog.Any("Error", err))
		return false
	}
	return true
}

// Publish a message to the stream.
//
//export Publish
func Publish(p C.uintptr_t, event, identifier, eventType, meta *C.char) bool {
	h := cgo.Handle(p)
	handler, ok := h.Value().(*StreamHandler)
	if !ok {
		// Creating a new logger here since if handler is nil, we don't have access to one.
		newLogger().Error("Failed to get stream handler from memory")
		return false
	}
	message := C.GoString(event)
	filter := stream.Filter{
		Identifier: C.GoString(identifier),
		Type:       C.GoString(eventType),
		Meta:       C.GoString(meta),
	}
	handler.publisher.Publish([]byte(message), filter)
	return true
}

// Close closes the publisher and the streamer.
//
//export Close
func Close(p C.uintptr_t) bool {
	h := cgo.Handle(p)
	// Delete the handle here, since it shall not be reused after close.
	defer h.Delete()
	handler, ok := h.Value().(*StreamHandler)
	if !ok {
		// Creating a new logger here since if handler is nil, we don't have access to one.
		newLogger().Error("Failed to get stream handler from memory")
		return false
	}
	if handler.publisher != nil {
		handler.publisher.Close()
	}
	if handler.consumer != nil {
		handler.consumer.Close()
	}
	if handler.streamer != nil {
		handler.streamer.Close()
	}
	return true
}

// newLogger creates a new logger.
func newLogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(os.Stdout, nil))
}
